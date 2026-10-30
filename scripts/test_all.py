"""Run reproducible Technical Gate; report real-material compatibility separately."""
from pathlib import Path
import argparse
import math
import json
import shutil
import sys
import tempfile
from harness_process import run_check
from harness_evidence import validate_partition

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = 'BLOCKED: REQUIRED MATERIAL UNAVAILABLE'


def run_all(project='all', timeout=600):
    checks = {name: {'status': 'NOT RUN', 'reason': 'NOT_SELECTED'} for name in ['auditdesk_python','webui_build','dsd_footing']}
    compatibility_result = {'status': 'NOT RUN', 'reason': 'AUDITDESK_NOT_SELECTED', 'checks': {}}
    if project in ['all','auditdesk']:
        with tempfile.TemporaryDirectory(prefix='harness_report_') as tmp:
            report = Path(tmp)/'auditdesk.json'
            command = [sys.executable,str(ROOT/'scripts/auditdesk_partition.py'),'--report',str(report)]
            py = run_check(command,ROOT/'auditdesk',timeout)
            checks['auditdesk_python'] = py
            if report.is_file() and py['reason']=='COMPLETED':
                try:
                    evidence = json.loads(report.read_text(encoding='utf-8'))
                    validate_partition(evidence)
                except (OSError, ValueError, KeyError, TypeError):
                    evidence = {'status':'FAIL','counts':{},'technical_checks':{},'compatibility_checks':{}}
                    py['reason'] = 'INVALID_EVIDENCE'
                py['counts'] = evidence['counts']
                py['status'] = evidence['status'] if py['exit_code']==0 else 'FAIL'
                py['checks'] = evidence['technical_checks']
                py['collected'] = evidence.get('collected', 0)
                py['collection_errors'] = evidence.get('collection_errors', 1)
                rows = evidence['compatibility_checks']
                statuses = {r['status'] for r in rows.values()}
                compatibility_result = {'status': BLOCKED if BLOCKED in statuses else 'NOT RUN', 'reason': 'MATERIAL_ASSESSMENT_ONLY', 'counts': {s:sum(r['status']==s for r in rows.values()) for s in ['PASS','FAIL','SKIP','NOT RUN',BLOCKED]}, 'checks': rows}
            else:
                if py['status'] == 'PASS':
                    py.update(status='FAIL',reason='MISSING_EVIDENCE')
                compatibility_result = {'status':'NOT RUN','reason':'COLLECTION_NOT_COMPLETED','checks':{}}
        npm=shutil.which('npm')
        if npm and (ROOT/'auditdesk/webui/node_modules').is_dir():
            checks['webui_build']=run_check([npm,'run','build'],ROOT/'auditdesk/webui',timeout)
        else:
            checks['webui_build']={'status':'NOT RUN','reason':'NPM_OR_NODE_MODULES_UNAVAILABLE'}
    if project in ['all','dsd_footing']:
        checks['dsd_footing']=run_check([sys.executable,str(ROOT/'scripts/test_dsd_footing.py')],ROOT,timeout)
    selected=[row for key,row in checks.items() if (project=='all' or key=='dsd_footing' and project=='dsd_footing' or key!='dsd_footing' and project=='auditdesk')]
    passed=bool(selected) and all(row['status']=='PASS' for row in selected)
    return {'technical_gate':'PASS' if passed else 'FAIL','technical_checks':checks,'real_material_compatibility':compatibility_result,
            'human_business_acceptance':'PENDING','scope':project,'counts':{s:sum(r['status']==s for r in checks.values()) for s in ['PASS','FAIL','SKIP','NOT RUN',BLOCKED]}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',choices=['all','auditdesk','dsd_footing'],default='all')
    parser.add_argument('--timeout',type=float,default=600,help='Maximum seconds per official check, including descendants')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout<=0:
        parser.error('positive timeout required')
    result=run_all(args.project,args.timeout)
    print('\n## 한눈에 보기')
    print('### 1. 이번에 무엇을 했나?\n새 환경에서 반복할 수 있는 자동검사를 실행했습니다.')
    print('### 2. 실제로 무엇이 달라졌나?\n반복 검사와 실제 자료 확인 결과를 따로 표시합니다.')
    print('### 3. 확인 결과는 어땠나?\n' + ('선택한 반복 검사는 통과했습니다.' if result['technical_gate']=='PASS' else '문제가 있거나 실행하지 못한 검사가 있습니다.'))
    reasons = {r.get('reason') for r in result['technical_checks'].values()}
    if 'TIMEOUT' in reasons:
        print('허용한 실행시간을 넘긴 검사가 있습니다. 해당 실행은 중단했습니다.')
    if 'EXECUTION_UNAVAILABLE' in reasons or 'NPM_OR_NODE_MODULES_UNAVAILABLE' in reasons:
        print('필요한 실행 도구나 설치 자료가 없어 실행하지 못한 검사가 있습니다.')
    print('### 4. 아직 남은 문제는?\n' + ('실제 자료 검사는 통과했습니다. 업무 확인은 별도입니다.' if result['real_material_compatibility']['status']=='PASS' else '실제 자료 확인은 완료되지 않았습니다. 자료 부족과 미실행 항목을 확인해야 합니다.'))
    print('### 5. 내가 결정해야 할 게 있나?\n있음. 실제 자료 확인과 업무상 수용 여부를 별도로 판단해야 합니다.')
    print('### 6. 지금 상태는?\n' + ('완료 후보. 전체 업무 수용 완료는 아닙니다.' if result['technical_gate']=='PASS' else '문제 발견. 실패와 미실행 원인을 확인해야 합니다.'))
    print('## Developer Details')
    console = json.loads(json.dumps(result))
    print('HARNESS_REPORT_JSON:' + json.dumps(console,ensure_ascii=True))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if result['technical_gate']!='PASS':
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
