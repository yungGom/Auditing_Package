"""Typed report validation; evidence absence never implies a PASS."""
import json
from pathlib import Path

BLOCKED = 'BLOCKED: REQUIRED MATERIAL UNAVAILABLE'
STATUSES = ('PASS', 'FAIL', 'SKIP', 'NOT RUN', BLOCKED)
MANIFEST = Path(__file__).with_name('auditdesk_compatibility.json')


def validate_partition(report):
    if not isinstance(report, dict) or report.get('status') not in STATUSES:
        raise ValueError('invalid partition status')
    technical, compatibility = report.get('technical_checks'), report.get('compatibility_checks')
    if not isinstance(technical, dict) or not technical or not isinstance(compatibility, dict):
        raise ValueError('missing collected evidence')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    expected = {r['selector'] for r in manifest['checks']}
    if {n.split('[', 1)[0] for n in compatibility} != expected:
        raise ValueError('incomplete compatibility inventory')
    if any(n.split('[', 1)[0] in expected for n in technical):
        raise ValueError('overlapping scopes')
    if not set(manifest.get('technical_marker_overrides', [])).issubset(technical):
        raise ValueError('missing pure calculation checks')
    for rows in (technical, compatibility):
        if any(not isinstance(r, dict) or r.get('status') not in STATUSES for r in rows.values()):
            raise ValueError('invalid check status')
    counts = {s: sum(r['status'] == s for r in technical.values()) for s in STATUSES}
    if report.get('counts') != counts or type(report.get('collected')) is not int or report['collected'] != len(technical) + len(compatibility):
        raise ValueError('inconsistent collection/count evidence')
    if type(report.get('collection_errors')) is not int or report['collection_errors'] < 0:
        raise ValueError('missing collection outcome')
    if report['status'] == 'PASS' and (report['collection_errors'] or counts['PASS'] != len(technical)):
        raise ValueError('contradictory partition PASS')


def validate_harness(report):
    if not isinstance(report, dict) or report.get('technical_gate') not in ('PASS', 'FAIL'):
        raise ValueError('invalid gate evidence')
    checks = report.get('technical_checks')
    if not isinstance(checks, dict) or set(checks) != {'auditdesk_python', 'webui_build', 'dsd_footing'}:
        raise ValueError('incomplete components')
    if any(not isinstance(r, dict) or r.get('status') not in STATUSES for r in checks.values()):
        raise ValueError('invalid component status')
    if report['technical_gate'] == 'PASS' and any(r['status'] != 'PASS' for r in checks.values()):
        raise ValueError('incomplete full gate')
    real = report.get('real_material_compatibility')
    if not isinstance(real, dict) or real.get('status') not in STATUSES or not isinstance(real.get('checks'), dict) or not real['checks']:
        raise ValueError('missing compatibility evidence')
    rows = real['checks']
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if {n.split('[', 1)[0] for n in rows} != {r['selector'] for r in manifest['checks']}:
        raise ValueError('incomplete compatibility inventory')
    if any(not isinstance(r, dict) or r.get('status') not in STATUSES for r in rows.values()):
        raise ValueError('invalid compatibility status')
    expected = BLOCKED if any(r['status'] == BLOCKED for r in rows.values()) else 'NOT RUN'
    if real['status'] != expected or any(r['status'] not in {BLOCKED, 'NOT RUN'} for r in rows.values()):
        raise ValueError('assessment cannot claim execution')

    audit = checks['auditdesk_python']
    validate_partition({'status': audit['status'], 'counts': audit.get('counts'),
                        'technical_checks': audit.get('checks'), 'compatibility_checks': rows,
                        'collected': audit.get('collected'), 'collection_errors': audit.get('collection_errors')})
