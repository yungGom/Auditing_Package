"""Read-only R6 reproducer; emits counts, never resource values.

Usage: python -B <this_file> <candidate-root> <public-workbook> <output-json>
Exit 1 means source/provenance cells were incorrectly emitted as Label resources.
This narrow check cannot certify namespace, applicability or all Label semantics.
"""
import sys,json,hashlib,collections,time,xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile
sys.dont_write_bytecode=True
root=Path(sys.argv[1]); source=Path(sys.argv[2]); output=Path(sys.argv[3]);sys.path.insert(0,str(root/'auditdesk'))
from auditdesk.xbrl_v2.taxonomy import parse_taxonomy_workbook,TaxonomyMetadata
raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest();t=time.monotonic()
snapshot=parse_taxonomy_workbook(raw,logical_uri='urn:review:official-workbook-unverified-context',metadata=TaxonomyMetadata('','UNVERIFIED_TAXONOMY','','','','',digest),namespaces=())
provenance_roles=('base schema','systemid','prohibit','comment')
counts=collections.Counter((l.language,l.role) for l in snapshot.labels)
false_labels=[l for l in snapshot.labels if l.role in provenance_roles]
ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
with ZipFile(source) as z:
    targets={r.attrib['Id']:r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    sheet=next(s for s in ET.fromstring(z.read('xl/workbook.xml')).find(ns+'sheets') if s.attrib['name']=='Label Link')
    target=targets[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
    path=target.lstrip('/') if target.startswith('/') else 'xl/'+target
    merges=[e.attrib['ref'] for _,e in ET.iterparse(z.open(path),events=('end',)) if e.tag==ns+'mergeCell']
summary={'source_sha256':digest,'parser_version':snapshot.parser_version,'seconds':round(time.monotonic()-t,3),'label_count':len(snapshot.labels),'language_group_label_counts':dict(collections.Counter(l.language for l in snapshot.labels if l.role not in provenance_roles)),'provenance_columns_as_labels':{role:sum(v for (lang,r),v in counts.items() if r==role) for role in provenance_roles},'provenance_labels_language_counts':dict(collections.Counter(l.language for l in false_labels)),'provenance_labels_source_columns':dict(collections.Counter(str(l.source.column) for l in false_labels)),'all_false_labels_have_row_and_source_snapshot':all(l.source.row>0 and l.source.snapshot_id==snapshot.snapshot_id for l in false_labels),'valid_language_block_label_count':len(snapshot.labels)-len(false_labels),'sheet_merge_ranges':merges,'label_resource_semantics_verdict':'FAIL' if false_labels else 'PASS','current_applicable':snapshot.current_applicable,'diagnostic_count':len(snapshot.diagnostics),'scope':'Counts/header/schema metadata only; no resource text, author, or private paths exported.'}
output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
assert len(false_labels)==0, 'Source/provenance columns must not become Label resources'
