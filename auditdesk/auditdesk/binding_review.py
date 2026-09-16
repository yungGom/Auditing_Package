"""Review projections and explicit atomic batches; no mapping or writer changes."""
import copy
from collections import Counter, defaultdict
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import re

from . import binding


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def enrich(draft):
    """Optional reviewed target identities, tied to the *current* layout hash.

    Existing source indexes remain valid. Without explicit target evidence we
    do not turn an ambiguous label-based layout proposal into a batch decision.
    """
    path = draft['paths'].get('current_source')
    if not path:
        return
    blob = Path(path).read_bytes()
    if binding.digest(blob) != draft['hashes']['current_source']:
        raise ValueError('현재 원천 index가 변경되었습니다')
    index = json.loads(blob)
    facts = index.get('facts', [])
    if not any(f.get('review_target_ids') for f in facts):
        return
    if index.get('layout_sha256') != draft['hashes']['layout']:
        raise ValueError('검토 대상 배치의 현재 layout hash가 필요합니다')
    sources = {s['id']:s for s in draft['sources']}
    targets = {t['id']:t for t in draft['targets']}
    for f in facts:
        ids = f.get('review_target_ids', [])
        if not isinstance(ids,list) or any(not isinstance(i,str) or i not in targets for i in ids):
            raise ValueError('현재 배치에 없는 검토 대상입니다')
        if ids:
            sources[f['source_id']]['review_target_ids'] = list(dict.fromkeys(ids))
            # This is explicit source evidence, never a new matching algorithm.
            for key in ids:
                cs = targets[key]['source_candidates']
                if not any(c['source_id']==f['source_id'] for c in cs):
                    cs.append({'source_id':f['source_id'],'evidence':['reviewed current target'],
                               'ambiguity_reasons':[]})


def _prior(draft, sources, concepts):
    suggestions = {}
    for old in draft.get('reuse_candidates', []):
        report = old.get('report', {})
        if any(report.get(k) != draft['report'][k] for k in ('company','scope')):
            continue
        oc = old['taxonomy']
        matches = [c for c in concepts if all(c.get(k)==oc.get(k) for k in ('prefix','name','role'))
                   and c.get('scope') in (None,draft['report']['scope'])]
        for s in sources:
            context = old.get('source_context', {})
            same_label = binding.normalize(s['label']) == binding.normalize(old.get('source_label',''))
            same_block = s['block_id'] == old.get('source_block_id')
            same_context = bool(context.get('section') and context.get('headers')
                and context['section']==s['section'] and context['headers']==s['headers'])
            if same_label and (same_block or same_context):
                for c in matches:
                    suggestions[(s['id'],c['id'])] = {'source_id':s['id'],'taxonomy_id':c['id'],
                        'prefix':c['prefix'],'name':c['name'],'role':c['role'],
                        'evidence':'이전 확정 기반 후보 · 현재 QName/Role 및 원문 문맥 일치 · 재검토 필요'}
    return list(suggestions.values())


def _proposal(draft, target, sources, concepts, roles):
    if len(sources)!=1:
        return None
    s=sources[0]
    if len(s.get('candidates',[]))!=1 or target['id'] not in s.get('review_target_ids',[]):
        return None
    c=concepts.get(s['candidates'][0]['id'])
    if not c or not s.get('source_evidence') or not s.get('context'):
        return None
    if any(s.get(k)!=c.get(k) or s.get(k) is None for k in ('prefix','name','role','data_type','period')):
        return None
    if s.get('scope')!=draft['report']['scope'] or c.get('scope')!=draft['report']['scope']:
        return None
    if len(roles[(c['prefix'],c['name'])])!=1:
        return None
    dims=s.get('dimensions')
    no_axes=not any(m['role']==c['role'] for m in draft['members'])
    if not isinstance(dims,list) or not (dims==c.get('dimensions') or (dims==[] and no_axes)):
        return None
    decision={'kind':'binding','source_id':s['id'],'taxonomy_id':c['id'],
              'context':copy.deepcopy(s['context']),'dimensions_reviewed':True,
              'source_evidence':s['source_evidence'],'manual':False}
    try: binding._validate(draft,target,decision)
    except (ValueError,TypeError,KeyError): return None
    return decision


def summarize(draft):
    states=binding.review_states(draft)
    sources={s['id']:s for s in draft['sources']}
    concepts={c['id']:c for c in draft['taxonomy']}
    roles=defaultdict(set)
    for c in concepts.values(): roles[(c['prefix'],c['name'])].add(c['role'])
    rows=[]; groups={}; progress={}; counts=Counter(); available=0
    for t in draft['targets']:
        ss=[sources[c['source_id']] for c in t['source_candidates'] if c['source_id'] in sources]
        ss=list({s['id']:s for s in ss}.values())
        cs=[c for s in ss for c in s.get('candidates',[]) if c['id'] in concepts]
        available+=bool(ss)
        exceptions=[]
        if not ss: exceptions.append('no_layout_candidate')
        if not ss or not cs: exceptions.append('source_insufficient')
        if len(ss)>1 or len(cs)>1: exceptions.append('multiple_candidates')
        reasons=[a for c in cs for a in c.get('ambiguity_reasons',[])]
        for field,code in [('period','period_mismatch'),('data_type','data_type_mismatch')]:
            if any(field+' mismatch' in a for a in reasons): exceptions.append(code)
        if not cs or any(c.get('dimensions') is None for c in cs): exceptions.append('dimension_uncertain')
        if any(c['prefix'] not in ('ifrs-full','dart') for c in cs): exceptions.append('company_extension')
        if any(len(roles[(c['prefix'],c['name'])])>1 for c in cs): exceptions.append('multiple_roles')
        proposal=_proposal(draft,t,ss,concepts,roles)
        st=states[t['id']]['state']
        if st in ('stale','conflict'):
            state=st; exceptions.append(st);proposal=None
        elif st in ('confirmed','manual'):
            state='confirmed';proposal=None
        elif proposal:
            state='high'
            if 'dimension_uncertain' in exceptions: exceptions.remove('dimension_uncertain')
        elif not cs: state='source_insufficient'
        elif all(c.get('confidence')=='low' for c in cs): state='low'
        else: state='medium'
        section='notes' if re.match(r'^\d+[.\s]',t['sheet']) or t['sheet'].startswith('주석') else 'body'
        decision=draft['decisions'].get(t['id'],{})
        selected=concepts.get(decision.get('taxonomy_id'))
        cc=([selected] if selected else cs)
        row={'id':t['id'],'sheet':t['sheet'],'section':section,'state':state,
             'roles':sorted({c['role'] for c in cc}),'data_types':sorted({c['data_type'] for c in cc}),
             'exceptions':exceptions,'candidate_available':bool(ss),
             'prior_suggestions':_prior(draft,ss,list(concepts.values())),'proposal':proposal}
        if proposal and 'company_extension' not in exceptions:
            c=concepts[proposal['taxonomy_id']]
            signature={k:c[k] for k in ('prefix','name','role','data_type','period')}
            signature['context']=proposal['context']
            key=hashlib.sha256(_canonical(signature).encode()).hexdigest()[:20]
            group=groups.setdefault(key,{'id':key,'signature':signature,'target_ids':[],
                'evidence':['exact current QName','same Role/DataType/Period/context',
                    'dimensions verified or no Role axes','scope match','no competing candidate',
                    'reviewed current target identity','current source hashes']})
            group['target_ids'].append(t['id']);row['group_id']=key
        rows.append(row);counts[state]+=1
        for key in ('sheet:'+t['sheet'],'section:'+section):
            p=progress.setdefault(key,{'required':0,'confirmed':0})
            p['required']+=1;p['confirmed']+=state=='confirmed'
    if counts['conflict'] or counts['stale']:
        groups.clear()
        for row in rows: row.pop('group_id',None)
    total=len(rows);confirmed=counts['confirmed'];batchable=sum(len(g['target_ids']) for g in groups.values())
    metrics={'required':total,'candidate_available':available,'no_candidate':total-available,
        'high_confidence':counts['high'],'medium_confidence':counts['medium'],'low_confidence':counts['low'],
        'source_insufficient':counts['source_insufficient'],'conflict':counts['conflict'],
        'confirmed':confirmed,'remaining':total-confirmed,'stale':counts['stale'],
        'manually_assigned':sum(r['state']=='confirmed' and draft['decisions'][r['id']].get('manual',False) for r in rows),
        'batch_confirmed':sum(r['state']=='confirmed' and bool(draft['decisions'][r['id']].get('batch_id')) for r in rows),
        'batch_reviewable':batchable,'individual_review_remaining':total-confirmed-batchable}
    for key,value in [('confirmation_pct',confirmed),('candidate_coverage_pct',available),
        ('high_confidence_reviewable_pct',batchable),('manual_review_required_pct',total-confirmed-batchable)]:
        metrics[key]=round(100*value/total,2) if total else 0
    return {'rows':rows,'metrics':metrics,'groups':list(groups.values()),'progress':progress,
            'exception_counts':dict(Counter(e for r in rows for e in r['exceptions']))}


def preview(draft, target_ids):
    if not isinstance(target_ids,list) or not target_ids or any(not isinstance(i,str) for i in target_ids):
        raise ValueError('일괄 검토 대상을 선택하세요')
    if len(set(target_ids))!=len(target_ids): raise ValueError('중복 대상입니다')
    r=summarize(draft); metrics=r['metrics']; by_id={row['id']:row for row in r['rows']}
    if metrics['stale'] or metrics['conflict']: raise ValueError('stale/conflict 0 상태에서만 일괄 확정할 수 있습니다')
    if any(i not in by_id or not by_id[i].get('group_id') for i in target_ids):
        raise ValueError('일괄 검토 근거가 부족하거나 대상 상태가 변경되었습니다')
    group_ids={by_id[i]['group_id'] for i in target_ids}
    if len(group_ids)!=1: raise ValueError('동일 근거 그룹을 선택하세요')
    group=next(g for g in r['groups'] if g['id'] in group_ids)
    selected=[row for row in r['rows'] if row['id'] in set(target_ids)]
    result={'revision':draft['revision'],'target_ids':[row['id'] for row in selected],
        'count':len(selected),'hashes':draft['hashes'],'conflicts':0,'stale':0,
        'sheets':sorted({row['sheet'] for row in selected}),
        'roles':sorted({role for row in selected for role in row['roles']}),
        'evidence':group['evidence'],'signature':group['signature'],
        'items':[{'target_id':row['id'],'decision':row['proposal']} for row in selected]}
    result['token']=hashlib.sha256(_canonical(result).encode()).hexdigest()
    return result


def confirm_batch(draft, target_ids, token, evidence):
    if not isinstance(evidence,str) or not evidence.strip(): raise ValueError('그룹과 대상 목록의 검토 근거를 입력하세요')
    p=preview(draft,target_ids)
    if not token or token!=p['token']: raise ValueError('미리보기 이후 검토 상태가 변경되었습니다. 다시 확인하세요')
    targets={t['id']:t for t in draft['targets']};sources={s['id']:s for s in draft['sources']}
    for item in p['items']: binding._validate(draft,targets[item['target_id']],item['decision'])
    out=copy.deepcopy(draft); now=datetime.now(timezone.utc).isoformat()
    for item in p['items']:
        d=item['decision'];out['decisions'][item['target_id']]={**d,'state':'confirmed',
            'reviewed_by':getpass.getuser(),'reviewed_at':now,'source_block_id':sources[d['source_id']]['block_id'],
            'source_evidence':d['source_evidence']+'; '+evidence.strip(),'batch_id':p['token']}
    if binding.stale(out): raise ValueError('원천이 변경되었습니다. 일괄 검토를 다시 실행하세요')
    out['revision']+=1
    out['review_metrics']=summarize(out)['metrics']
    return out
