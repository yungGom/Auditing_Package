"""Read-only Issue #11 acceptance probes using fresh synthetic OOXML inputs.

Run against an existing candidate repository; no candidate file is changed.
JSON goes to stdout unless --output names a result file. Test progress goes to
stderr. Exit 1 means at least one acceptance assertion failed.
"""
import argparse
import sys
import json
import unittest
from pathlib import Path
from hashlib import sha256
from dataclasses import replace


arguments = argparse.ArgumentParser(description=__doc__)
arguments.add_argument('--candidate-root', required=True, type=Path,
                       help='Root of the existing candidate repository')
arguments.add_argument('--output', type=Path,
                       help='Optional JSON result path; default is stdout')
args = arguments.parse_args()
candidate_root = args.candidate_root.resolve()
ROOT = candidate_root / 'auditdesk'
for required in (ROOT / 'tests' / 'test_xbrl_v2_taxonomy.py',
                 ROOT / 'auditdesk' / 'xbrl_v2' / 'taxonomy.py'):
    if not required.is_file():
        arguments.error('Candidate repository lacks required file: ' + str(required.relative_to(candidate_root)))
if args.output and args.output.resolve().is_relative_to(candidate_root):
    arguments.error('--output must stay outside the candidate repository')
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from test_xbrl_v2_taxonomy import parse, edited, workbook
from auditdesk.xbrl_v2.taxonomy import NamespaceBinding, parse_taxonomy_workbook


def summarize(snapshot):
    return {
        'current_applicable': snapshot.current_applicable,
        'diagnostics': [d.code for d in snapshot.diagnostics],
        'concepts': len(snapshot.concepts), 'roles': len(snapshot.roles),
        'occurrences': len(snapshot.occurrences),
        'references': len(snapshot.references),
        'occurrence_ids_unique': len({o.occurrence_id for o in snapshot.occurrences}) == len(snapshot.occurrences),
        'labels': [(l.language, l.role, l.text) for l in snapshot.labels],
    }


def duplicate_role_id(w):
    w['RoleTypes'].append([2, 'r', 'urn:role:b', 'presentationLink', 'Second role'])


cases = {
    'control': parse(),
    'duplicate_concept_source_id': parse(edited(lambda w: setattr(w['Concepts']['D3'], 'value', 'cash'))),
    'duplicate_role_source_id': parse(edited(duplicate_role_id)),
    'duplicate_role_uri': parse(edited(lambda w: w['RoleTypes'].append([2, 'r2', 'urn:role:a', 'presentationLink', 'Conflicting role']))),
    'missing_second_presentation_header': parse(edited(lambda w: w['Presentation Link'].delete_rows(8, 1))),
    'repeated_same_qname_role_path': parse(),
    'blank_arcrole': parse(edited(lambda w: setattr(w['Presentation Link']['J5'], 'value', None))),
    'blank_order': parse(edited(lambda w: setattr(w['Presentation Link']['G5'], 'value', None))),
}
data = workbook()
meta = parse(data).metadata
extension_like_data = edited(lambda w: w['Concepts'].append([3, 'ext', 'Cash', 'extcash', 'xbrli:monetaryItemType', 'instant', 'false']))
cases['same_local_name_distinct_namespaces'] = parse_taxonomy_workbook(
    extension_like_data,
    logical_uri='public:taxonomy.xlsx',
    metadata=replace(meta, content_sha256=sha256(extension_like_data).hexdigest()),
    namespaces=(NamespaceBinding('ifrs', 'urn:ifrs:2026', 'standard declaration'), NamespaceBinding('ext', 'urn:ext:2026', 'extension declaration')))
cases['current_extension_source_role'] = parse(source_role='CURRENT_EXTENSION')
output = {name: summarize(snapshot) for name, snapshot in cases.items()}


class AcceptanceProbes(unittest.TestCase):
    def test_duplicate_concept_source_identifier_is_explicit(self):
        s = cases['duplicate_concept_source_id']
        self.assertFalse(s.current_applicable, 'Repeated source Concepts.id is silently accepted')
        self.assertTrue(s.diagnostics)

    def test_duplicate_role_source_identifier_is_explicit(self):
        s = cases['duplicate_role_source_id']
        self.assertFalse(s.current_applicable, 'Repeated source RoleTypes.id is silently accepted')
        self.assertTrue(s.diagnostics)

    def test_every_presentation_section_requires_a_header(self):
        s = cases['missing_second_presentation_header']
        self.assertFalse(s.current_applicable, 'A whole presentation section disappears without diagnostic')
        self.assertTrue(s.diagnostics)

    def test_duplicate_role_uri_fails_closed(self):
        self.assertFalse(cases['duplicate_role_uri'].current_applicable)
        self.assertIn('AMBIGUOUS_ROLE', output['duplicate_role_uri']['diagnostics'])

    def test_expanded_namespaces_distinguish_same_local_name(self):
        s = cases['same_local_name_distinct_namespaces']
        self.assertTrue(s.current_applicable)
        self.assertNotEqual(s.concepts[0].qname, s.concepts[-1].qname)

    def test_repeated_qname_role_path_occurrences_survive(self):
        s = cases['repeated_same_qname_role_path']
        self.assertEqual(len(s.occurrences), 4)
        self.assertEqual(len({o.occurrence_id for o in s.occurrences}), 4)
        self.assertEqual((s.occurrences[1].qname,s.occurrences[1].role_uri,s.occurrences[1].path),
                         (s.occurrences[3].qname,s.occurrences[3].role_uri,s.occurrences[3].path))

    def test_role_label_reference_keep_workbook_provenance(self):
        s = cases['control']
        self.assertEqual({(l.language,l.role) for l in s.labels}, {('ko','label'),('ko','verboseLabel'),('en','label')})
        self.assertEqual(s.references[0].parts, (('Name','IAS'),('Number','7'),('Paragraph','6')))
        self.assertTrue(all(r.source.snapshot_id==s.snapshot_id and r.source.sheet and r.source.row>0
                            for r in (*s.roles,*s.labels,*s.references)))

    def test_unsupported_extension_role_is_explicitly_rejected(self):
        self.assertFalse(cases['current_extension_source_role'].current_applicable)
        self.assertIn('NON_CURRENT_SOURCE', output['current_extension_source_role']['diagnostics'])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AcceptanceProbes)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    payload = {
        'cases': output,
        'test_results': {
            'run': result.testsRun,
            'passed': result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
            'failed': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped),
            'failing_tests': [test._testMethodName for test, _ in result.failures],
        },
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered, encoding='utf-8')
    else:
        print(rendered, end='')
    raise SystemExit(0 if result.wasSuccessful() else 1)
