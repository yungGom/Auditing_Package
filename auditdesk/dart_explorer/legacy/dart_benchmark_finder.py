"""
DART 벤치마크 XBRL 검색기  (로컬 실행 전용)
────────────────────────────────────────────────────────────
목적: 특정 XBRL 자문법인이 작성하고, 특정 업종코드인 회사의 XBRL 공시를
      OpenDART에서 찾아, 벤치마크로 삼을 수 있게 수집한다.

원리:
  1) OpenDART 공시검색(list)으로 대상 기간의 정기보고서 목록 수집
  2) 각 회사 재무제표 원본(XBRL) 다운로드 (fnlttXbrl)
  3) XBRL 안의 dart-gcd 태그에서 자문법인·업종코드·감사인·회사명 추출
       - 자문법인 = AuthorName 중 contextRef가 XBRLConsultingFirmMember 인 값
         (회사가 직접 작성했으면 'Self-written' 으로 표기됨)
  4) (자문법인 = 지정법인)  AND/OR  (업종코드 = 지정코드) 로 필터
  5) 조건에 맞는 회사 목록 + XBRL 경로 저장 → xbrl_extract.py 로 내용 확인

주의:
  - 자문법인은 XBRL 파일의 XBRLConsultingFirmMember 태그에서 직접 읽는다(감사인과 별개).
  - OpenDART API 키가 필요하다. https://opendart.fss.or.kr 에서 무료 발급.
  - 회사 데이터는 로컬에만 저장된다(클라우드 업로드 없음).

필요 패키지:  pip install requests lxml
사용 예:
  python dart_benchmark_finder.py --key YOURKEY --firm 삼일회계법인 \
         --sic 41112 --start 20250101 --end 20250930 --limit 20
"""
import os, sys, io, csv, time, zipfile, argparse, glob
import requests
from lxml import etree

BASE = 'https://opendart.fss.or.kr/api'
GCD = '{http://dart.fss.or.kr/taxonomy/2024-06-30/ifrs/dart-gcd}'  # 연도 바뀌면 자동 대응(아래 localname 매칭 사용)

# ── OpenDART 호출 ────────────────────────────────────────────
def list_disclosures(key, start, end, kind='A', corp=None, max_pages=100):
    """공시검색: 기간 내 정기보고서(kind='A') 목록"""
    out, page = [], 1
    while page <= max_pages:
        p = dict(crtfc_key=key, bgn_de=start, end_de=end, page_no=page,
                 page_count=100, pblntf_ty=kind, last_reprt_at='Y')
        if corp: p['corp_code'] = corp
        r = requests.get(f'{BASE}/list.json', params=p, timeout=30).json()
        if r.get('status') != '000':
            if page == 1: print('  [list] 응답:', r.get('status'), r.get('message'))
            break
        out += r.get('list', [])
        if page >= int(r.get('total_page', 1)): break
        page += 1; time.sleep(0.2)
    return out

def download_xbrl(key, rcept_no, save_dir):
    """재무제표 원본파일(XBRL) zip 다운로드 후 .xbrl 경로 반환"""
    p = dict(crtfc_key=key, rcept_no=rcept_no, reprt_code='11012')  # 11012=반기, 11011=사업, 11013=1분기,11014=3분기
    r = requests.get(f'{BASE}/fnlttXbrl.xml', params=p, timeout=60)
    if r.headers.get('content-type', '').startswith('application/json'):
        return None  # 오류(JSON)면 XBRL 없음
    d = os.path.join(save_dir, rcept_no); os.makedirs(d, exist_ok=True)
    try:
        z = zipfile.ZipFile(io.BytesIO(r.content)); z.extractall(d)
    except zipfile.BadZipFile:
        return None
    xf = glob.glob(os.path.join(d, '*.xbrl'))
    return xf[0] if xf else None

# ── XBRL에서 회사개황(dart-gcd) 추출 ─────────────────────────
def _find_texts(root, localname):
    """네임스페이스 무관하게 localname으로 태그 텍스트 수집"""
    vals = []
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.split('}')[-1] == localname and el.text:
            vals.append(el.text.strip())
    return vals

def _find_by_member(root, localname, member_kw, lang='ko'):
    """AuthorName 처럼 contextRef의 Member로 구분되는 태그에서 특정 멤버 값 추출"""
    for el in root.iter():
        if not isinstance(el.tag, str) or el.tag.split('}')[-1] != localname:
            continue
        cref = el.get('contextRef') or ''
        lg = el.get('{http://www.w3.org/XML/1998/namespace}lang')
        if member_kw in cref and (lg == lang or lg is None) and el.text:
            return el.text.strip()
    return ''

def profile_from_xbrl(xbrl_path):
    root = etree.parse(xbrl_path).getroot()
    def first(name):
        v = _find_texts(root, name); return v[0] if v else ''
    # 감사인: 당기 값 우선(여러 기간 태깅됨) → 마지막이 보통 당기
    auditors = _find_texts(root, 'SeparatedAuditorName') or _find_texts(root, 'ConsolidatedAuditorName')
    auditor_now = auditors[-1] if auditors else ''
    # ★ XBRL 자문법인: AuthorName 중 XBRLConsultingFirmMember 구성요소 값
    consulting = _find_by_member(root, 'AuthorName', 'XBRLConsultingFirmMember', 'ko')
    return dict(
        회사명=first('EntityRegistrantName'),
        업종코드=first('StandardIndustryCode'),
        XBRL자문법인=consulting,            # 'Self-written' 이면 회사 자체작성
        감사인=auditor_now,
        감사인전체='|'.join(dict.fromkeys(auditors)),
        상장시장=first('DomesticExchange'),
        결산월=first('EntityFiscalMonth'),
        문서제목=first('DocumentTitle'),
    )

# ── 메인 검색 ────────────────────────────────────────────────
def run(key, firm, sic, start, end, kind, outdir, note_keyword=None, limit=None):
    os.makedirs(outdir, exist_ok=True)
    xbrl_dir = os.path.join(outdir, 'xbrl'); os.makedirs(xbrl_dir, exist_ok=True)
    print(f'[1] 공시목록 수집 {start}~{end} (kind={kind})...')
    docs = list_disclosures(key, start, end, kind)
    print(f'    {len(docs)}건')
    seen, hits = set(), []
    for i, d in enumerate(docs, 1):
        corp = d.get('corp_code'); rcept = d.get('rcept_no')
        if corp in seen: continue
        seen.add(corp)
        if limit and len(hits) >= limit: break
        try:
            xp = download_xbrl(key, rcept, xbrl_dir)
            if not xp: continue
            prof = profile_from_xbrl(xp)
        except Exception as e:
            continue
        # 필터: 자문법인/업종 (지정된 조건만 적용, 둘 다 지정 시 AND)
        ok = True
        if firm:
            fv = prof['XBRL자문법인'] or ''
            # 'Self-written'(자체작성)은 자문법인 지정 검색에서 제외
            if firm not in fv or fv.lower() == 'self-written':
                ok = False
        if sic and str(prof['업종코드']) != str(sic): ok = False
        if not ok: continue
        prof.update(rcept_no=rcept, corp_code=corp, xbrl=xp,
                    접수일=d.get('rcept_dt'), 보고서명=d.get('report_nm'))
        hits.append(prof)
        print(f'    ✔ {prof["회사명"]} | 자문 {prof["XBRL자문법인"]} | 감사인 {prof["감사인"]} | 업종 {prof["업종코드"]}')
        time.sleep(0.3)
    # 결과 저장
    res = os.path.join(outdir, 'benchmark_results.csv')
    if hits:
        with open(res, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(hits[0].keys())); w.writeheader(); w.writerows(hits)
    print(f'[2] 조건 충족 {len(hits)}건 -> {res}')
    print(f'    XBRL 원본: {xbrl_dir}/  (xbrl_extract.py 로 내용 확인 가능)')
    return hits

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--key', required=True, help='OpenDART 인증키')
    ap.add_argument('--firm', default='', help='XBRL 자문법인명(예: 삼일회계법인). 파일의 XBRLConsultingFirmMember 기준')
    ap.add_argument('--sic', default='', help='업종코드(예: 41112)')
    ap.add_argument('--start', required=True, help='시작일 YYYYMMDD')
    ap.add_argument('--end', required=True, help='종료일 YYYYMMDD')
    ap.add_argument('--kind', default='A', help='공시유형(A=정기보고서)')
    ap.add_argument('--out', default='./benchmark_out', help='결과 폴더')
    ap.add_argument('--limit', type=int, default=None, help='최대 수집 건수(테스트용)')
    a = ap.parse_args()
    if not a.firm and not a.sic:
        print('자문법인(--firm) 또는 업종(--sic) 중 하나는 지정하세요.'); sys.exit(1)
    run(a.key, a.firm, a.sic, a.start, a.end, a.kind, a.out, limit=a.limit)
