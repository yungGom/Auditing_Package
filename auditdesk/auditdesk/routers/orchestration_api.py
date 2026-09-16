"""Workflow lifecycle shares the existing durable binding ID and gate."""
import json
import uuid
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException
from .. import orchestration, jobs
from . import binding_api, explorer

router=APIRouter()


@router.post('/analyze')
def analyze(body: dict):
    return binding_api._error(lambda: orchestration.analyze(body['dsd']))


@router.get('/assets')
def assets():
    from dart_explorer.xbrl.taxonomy_diff import TAXONOMY_DIR
    from dart_explorer.xbrl.corpus import DEFAULT_DB
    root=Path(TAXONOMY_DIR)
    return {'taxonomy_assets':[str(p) for p in sorted(root.rglob('*')) if p.suffix.lower() in ('.xls','.xlsm','.xsd')],
            'corpus':DEFAULT_DB if Path(DEFAULT_DB).is_file() else None,
            'message':'로컬 자산은 적용기간/회사 검토가 필요합니다. 최신 파일을 자동 정답으로 선택하지 않습니다.'}


@router.post('/prior-search')
def prior_search(body: dict):
    cli=explorer._client()
    try:
        return orchestration.find_prior(cli,body['company'],body['period_end'],body['report_type'])
    except (KeyError,ValueError):
        raise HTTPException(422,'회사·보고기간·보고서 종류를 확인하세요') from None
    except Exception:
        raise HTTPException(502,'회사/전기 공시 검색 실패 — OpenDART 연결 및 회사명을 확인하세요') from None


def _create(body, progress=lambda message:None):
    prior_loader=None
    if body.get('mode')=='rollforward' and body.get('fetch_prior',True):
        from ..orchestration_sources import acquire_prior
        prior_loader=lambda:acquire_prior(explorer._client(),body)
    draft=orchestration.prepare(body,progress=progress,prior_loader=prior_loader)
    draft['id']=uuid.uuid4().hex
    if body.get('reuse_id'):
        with binding_api._connect() as con: old=binding_api._load(con,body['reuse_id'])
        if any(old['report'][k]!=draft['report'][k] for k in ('company','scope')):
            raise ValueError('이전 확정 이력의 회사/범위가 다릅니다')
        source_by_id={s['id']:s for s in old['sources']}
        taxonomy_by_id={c['id']:c for c in old['taxonomy']}
        draft['reuse_candidates']=[{'source_label':source_by_id[d['source_id']]['label'],
            'taxonomy':taxonomy_by_id[d['taxonomy_id']],'report':old['report'],
            'source_block_id':d['source_block_id'],'source_context':{k:source_by_id[d['source_id']].get(k) for k in ('section','headers')},
            'previous_hashes':old['hashes'],'state':'recheck_required'}
            for d in old['decisions'].values() if d['kind']=='binding']
        draft['workflow']['history']={'origin':'USER_CONFIRMED_HISTORY','id':old['id'],
            'revision':old['revision'],'message':'이전 확정은 후보 근거로만 사용; 새 기간에는 미확정'}
    with binding_api._connect() as con:
        con.execute('INSERT INTO binding_reviews VALUES(?,?)',(draft['id'],json.dumps(draft,ensure_ascii=False)))
    return binding_api._view(draft)


@router.post('')
def create(body: dict):
    return binding_api._error(lambda: _create(body))


@router.post('/start',status_code=202)
def start(body: dict):
    # Check missing key synchronously, before a background job can mask it.
    if body.get('mode')=='rollforward' and body.get('fetch_prior',True): explorer._client()
    def run(progress):
        stages=['당기 DSD 분석']+(['회사 전기 공시 검색·수신'] if body.get('mode')=='rollforward' else [])+['현재 taxonomy 및 배치 후보 생성','공시 corpus 근거 연결','추천 근거 정리']
        def stage_progress(message):
            progress(message,stages.index(message)+1 if message in stages else None,len(stages)+2)
        try:
            draft=binding_api._error(lambda: _create(body,stage_progress))
            return {'id':draft['id']}
        except HTTPException as e:
            # jobs preserves actionable 4xx messages and strips internal trace
            # from UI; retain external failures as an explicit result status.
            return {'state':'failed','status':e.status_code,'message':e.detail}
    return {'job_id':jobs.submit('xbrl-orchestration',run)}


@router.get('')
def workflows():
    with binding_api._connect() as con:
        drafts=[json.loads(r[0]) for r in con.execute('SELECT payload FROM binding_reviews ORDER BY rowid DESC')]
    return {'workflows':[{'id':d['id'],'report':d['report'],'mode':d['workflow']['mode']} for d in drafts if 'workflow' in d]}


@router.get('/{key}')
def read(key: str):
    with binding_api._connect() as con: draft=binding_api._load(con,key)
    if 'workflow' not in draft: raise HTTPException(404,'해당 전환 작업이 없습니다')
    orchestration.refresh(draft)
    return binding_api._view(draft)


@router.get('/{key}/reference')
def reference_detail(key: str, reference_id: str, offset: int=0):
    from .. import binding
    with binding_api._connect() as con: draft=binding_api._load(con,key)
    ref=next((r for r in draft.get('workflow',{}).get('references',[]) if r['id']==reference_id),None)
    if ref is None: raise HTTPException(404,'해당 작업의 참고 근거가 없습니다')
    if offset<0: raise HTTPException(422,'사례 위치가 올바르지 않습니다')
    if binding.stale(draft): raise HTTPException(409,'원천이 변경되었습니다. 다시 분석 후 확인하세요')
    path=Path(draft['paths']['reference_corpus'])
    try:
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as con:
            con.row_factory=sqlite3.Row
            rows=con.execute('SELECT u.corp_code,c.corp_name,u.label_ko,u.roles,u.dims,c.induty_code '
                'FROM usages u JOIN companies c ON c.corp_code=u.corp_code '
                'WHERE u.element_id=? AND c.status=? AND c.corp_name!=? AND c.corp_code!=? '
                'ORDER BY u.corp_code LIMIT 21 OFFSET ?',
                (ref['prefix']+'_'+ref['name'],'ok',draft['report']['company'],draft['report']['company'].removeprefix('entity'),offset)).fetchall()
    except sqlite3.DatabaseError:
        raise HTTPException(422,'corpus 원천을 읽을 수 없습니다') from None
    return {'reference_id':reference_id,'origin':'OPENDART_REFERENCE','offset':offset,
            'rows':[dict(row) for row in rows[:20]],'has_more':len(rows)>20,
            'sha256':draft['hashes']['reference_corpus'],
            'message':'타사 사용 원문입니다. 현재 회사의 기간/차원으로 자동 적용하지 않습니다.'}
