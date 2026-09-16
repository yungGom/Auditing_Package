"""Durable Studio binding review; revision checks prevent lost decisions."""
import json
import uuid
import zipfile
import xlrd

from fastapi import APIRouter, HTTPException

from .. import binding, binding_review, jobs

router = APIRouter()


def _connect():
    con = jobs.connect()
    con.execute('CREATE TABLE IF NOT EXISTS binding_reviews(id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    return con


def _load(con, key):
    row = con.execute('SELECT payload FROM binding_reviews WHERE id=?',(key,)).fetchone()
    if not row: raise HTTPException(404,'검토 작업을 찾을 수 없습니다')
    return json.loads(row[0])


def _view(draft):
    return {**draft,'coverage':binding.coverage(draft),'target_states':binding.review_states(draft),
            'review':binding_review.summarize(draft)}


def _updated_view(draft, target_ids, compact=False):
    if not compact:
        return _view(draft)
    # Preserve the default API contract; the review UI already has immutable
    # source/taxonomy/layout data and only needs current decisions and queues.
    return {'partial':True,'id':draft['id'],'revision':draft['revision'],
        'decision_updates':{key:draft['decisions'].get(key) for key in target_ids},
        'coverage':binding.coverage(draft),'target_states':binding.review_states(draft),
        'review':binding_review.summarize(draft)}


def _error(action):
    try: return action()
    except (zipfile.BadZipFile, xlrd.XLRDError):
        raise HTTPException(422,'DSD 또는 BIFF8 .xls 원천 파일의 형식을 확인하세요') from None
    except (ValueError,KeyError,TypeError) as e:
        raise HTTPException(422, str(e) if isinstance(e,ValueError) else '입력 필드와 형식을 확인하세요') from None
    except OSError:
        raise HTTPException(409,'원천/산출 경로를 확인하세요. 기존 산출 폴더는 덮어쓰지 않습니다.') from None


@router.get('')
def drafts():
    with _connect() as con:
        rows = con.execute('SELECT id,payload FROM binding_reviews ORDER BY rowid DESC').fetchall()
    return {'drafts':[{'id':key,'report':json.loads(payload)['report']} for key,payload in rows]}


@router.post('')
def create(body: dict):
    def run():
        draft = binding.prepare(body['dsd'],body['taxonomy'],body['layout'],body['report'],body.get('current_source'))
        binding_review.enrich(draft)
        draft['id'] = uuid.uuid4().hex
        if body.get('reuse_id'):
            with _connect() as con: old = _load(con,body['reuse_id'])
            if (old['report']['company'],old['report']['scope']) != (draft['report']['company'],draft['report']['scope']):
                raise ValueError('다른 회사/범위의 binding은 재사용할 수 없습니다')
            # Keep history as proposals only; offsets are never transferred.
            draft['reuse_candidates'] = [
                {'source_label':next(s['label'] for s in old['sources'] if s['id'] == d['source_id']),
                 'taxonomy':next(c for c in old['taxonomy'] if c['id'] == d.get('taxonomy_id')),
                 'report':old['report'],'source_block_id':d['source_block_id'],
                 'source_context':next({k:s.get(k) for k in ('section','headers')} for s in old['sources'] if s['id']==d['source_id']),
                 'previous_hashes':old['hashes'],'state':'recheck_required'}
                for d in old['decisions'].values() if d['kind'] == 'binding']
        draft['review_metrics']=binding_review.summarize(draft)['metrics']
        with _connect() as con:
            con.execute('INSERT INTO binding_reviews VALUES(?,?)',(draft['id'],json.dumps(draft,ensure_ascii=False)))
        return _view(draft)
    return _error(run)


@router.get('/{key}')
def read(key: str):
    with _connect() as con: return _view(_load(con,key))


@router.put('/{key}')
def decide(key: str, body: dict):
    def run():
        with _connect() as con:
            con.execute('BEGIN IMMEDIATE')
            draft = _load(con,key)
            if body.get('revision') != draft['revision']: raise HTTPException(409,'다른 검토에서 변경되었습니다. 새로고침 후 확인하세요')
            updated = binding.decide(draft,body['target_id'],body['decision'])
            updated['review_metrics']=binding_review.summarize(updated)['metrics']
            con.execute('UPDATE binding_reviews SET payload=? WHERE id=?',(json.dumps(updated,ensure_ascii=False),key))
        return _updated_view(updated,[body['target_id']],body.get('compact') is True)
    return _error(run)


@router.post('/{key}/batch-preview')
def batch_preview(key: str, body: dict):
    def run():
        with _connect() as con:
            draft=_load(con,key)
        if body.get('revision')!=draft['revision']:
            raise HTTPException(409,'검토 상태가 변경되었습니다. 새로고침 후 확인하세요')
        return binding_review.preview(draft,body.get('target_ids'))
    return _error(run)


@router.post('/{key}/batch-confirm')
def batch_confirm(key: str, body: dict):
    def run():
        with _connect() as con:
            con.execute('BEGIN IMMEDIATE')
            draft=_load(con,key)
            if body.get('revision')!=draft['revision']:
                raise HTTPException(409,'다른 검토에서 변경되었습니다. 새로고침 후 확인하세요')
            updated=binding_review.confirm_batch(draft,body.get('target_ids'),body.get('token'),body.get('evidence'))
            con.execute('UPDATE binding_reviews SET payload=? WHERE id=?',(json.dumps(updated,ensure_ascii=False),key))
        return _updated_view(updated,body['target_ids'],body.get('compact') is True)
    return _error(run)


@router.post('/{key}/generate')
def generate(key: str, body: dict):
    def run():
        with _connect() as con:
            con.execute('BEGIN IMMEDIATE')
            draft = _load(con,key)
            if body.get('revision') != draft['revision']: raise HTTPException(409,'검토 상태가 변경되었습니다. 다시 확인하세요')
            return binding.generate(draft,body['out_dir'])
    return _error(run)
