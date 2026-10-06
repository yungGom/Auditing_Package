"""Explicit AuditDesk partition; existing product tests/expectations are untouched."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'auditdesk'
MANIFEST = Path(__file__).with_name('auditdesk_compatibility.json')
BLOCKED = 'BLOCKED: REQUIRED MATERIAL UNAVAILABLE'


def selector(nodeid):
    return nodeid.split('[', 1)[0]


class Partition:
    def __init__(self, mode, manifest):
        self.mode = mode
        self.material = {r['selector']: r['material'] for r in manifest['checks']}
        if len(self.material) != len(manifest['checks']):
            raise ValueError('duplicate compatibility selector')
        self.required_paths = {r['selector']: r.get('required_paths', []) for r in manifest['checks']}
        if any(Path(path).is_absolute() or '..' in Path(path).parts
               for paths in self.required_paths.values() for path in paths):
            raise ValueError('material prerequisites must stay inside the repository')
        self.overrides = set(manifest.get("technical_marker_overrides", []))
        self.safe_ids = {}
        self.case_counts = {}
        self.technical = {}
        self.compatibility = {}
        self.collection_errors = 0

    def pytest_collectreport(self, report):
        if report.failed:
            self.collection_errors += 1

    def pytest_collection_modifyitems(self, session, config, items):
        import pytest
        kept, removed = [], []
        matched = set()
        for item in items:
            base = selector(item.nodeid)
            # Never serialize pytest parameter labels: they may contain workstation/client paths.
            self.case_counts[base] = self.case_counts.get(base, 0) + 1
            safe = base if '[' not in item.nodeid else f'{base}[case:{self.case_counts[base]}]'
            self.safe_ids[item.nodeid] = safe
            if base in self.overrides:
                # These four reviewed tests use only literal numeric arrays, no material fixture.
                # Remove the module's availability mark for these items only; retain any own/new mark.
                module_marks = getattr(item.module, 'pytestmark', [])
                if not isinstance(module_marks, (list, tuple)):
                    module_marks = [module_marks]
                ignored = {id(m.mark if hasattr(m, 'mark') else m) for m in module_marks
                           if m.name == 'skipif'}
                original = item.iter_markers
                item.iter_markers = lambda name=None, original=original, ignored=ignored: (
                    m for m in original(name) if id(m) not in ignored)

            if base not in self.material:
                self.technical[safe] = {'status': 'NOT RUN'}
                if self.mode == 'technical':
                    kept.append(item)
                else:
                    removed.append(item)
                continue
            matched.add(base)
            # Existing data availability markers are evidence, not a new expected result.
            unavailable = any(any(bool(c) for c in m.args) for m in item.iter_markers('skipif'))
            if base.endswith('::test_g2_smoke_direct'):
                unavailable = not item.module._KNOWN_GENERATIONS
            # Old tests may refer to private workstation paths. Do not execute those from this Harness.
            outside = any(isinstance(v, str) and Path(v).is_absolute() and not Path(v).resolve().is_relative_to(PROJECT.resolve())
                          for k,v in vars(item.module).items() if k.startswith('_') and k not in {'__file__','__cached__'})
            paths = [PROJECT / path for path in self.required_paths[base]]
            escaped = any(not path.resolve().is_relative_to(PROJECT.resolve()) for path in paths)
            missing = escaped or any(not path.exists() for path in paths)
            unavailable = unavailable or outside or missing
            row = {'status': BLOCKED if unavailable else 'NOT RUN', 'material': self.material[base]}
            if outside or escaped:
                row['reason'] = 'OUTSIDE_REPOSITORY_MATERIAL_NOT_AUTHORIZED'
            elif missing:
                row['reason'] = 'MISSING_REQUIRED_MATERIAL'
            self.compatibility[safe] = row
            # Assessment only: no boolean flag can authorize arbitrary local material.
            removed.append(item)
        # Deleted/renamed catalogued checks must not disappear silently.
        if self.material.keys() - matched or self.overrides - set(self.case_counts):
            raise pytest.UsageError('compatibility catalog contains missing tests; explicit review required')
        items[:] = kept
        config.hook.pytest_deselected(items=removed)

    def pytest_runtest_logreport(self, report):
        target = self.compatibility if selector(report.nodeid) in self.material else self.technical
        row = target.setdefault(self.safe_ids.get(report.nodeid, selector(report.nodeid)), {'status': 'NOT RUN'})
        if report.failed:
            row['status'] = 'FAIL'
        elif report.skipped and row['status'] != 'FAIL':
            # Runtime-only missing materials retain the original skip evidence.
            row['status'] = 'SKIP'
        elif report.when == 'call' and report.passed and row['status'] not in {'FAIL', 'SKIP'}:
            row['status'] = 'PASS'

    def result(self, code):
        records = self.technical if self.mode == 'technical' else self.compatibility
        counts = {key: sum(r['status'] == key for r in records.values()) for key in ['PASS','FAIL','SKIP','NOT RUN',BLOCKED]}
        status = 'FAIL' if self.collection_errors or code not in (0,5) or counts['FAIL'] else ('PASS' if counts['PASS'] and not any(counts[k] for k in ['SKIP','NOT RUN',BLOCKED]) else BLOCKED if counts[BLOCKED] else 'NOT RUN')
        if self.mode == 'technical' and status != 'PASS':
            status = 'FAIL'
        return {'status': status, 'counts': counts, 'collection_errors': self.collection_errors,
                'technical_checks': self.technical, 'compatibility_checks': self.compatibility,
                'collected': len(self.safe_ids)}


def main():
    import pytest
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['technical','compatibility'], default='technical')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    plugin = Partition(args.mode, json.loads(MANIFEST.read_text(encoding='utf-8-sig')))
    with tempfile.TemporaryDirectory(prefix='harness_auditdesk_') as tmp:
        code = pytest.main(['dsd_workbench/dsd_tool/tests','dart_explorer/tests','tests','-q','-ra',f'--basetemp={Path(tmp)/"pytest"}'], plugins=[plugin])
    result = plugin.result(code)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if result['status'] == 'PASS' else 2 if result['status'] in {BLOCKED,'NOT RUN'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
