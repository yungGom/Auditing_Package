"""OpenDART adapters. Prior facts remain provenance, never current values."""
from pathlib import Path
from datetime import date
import zipfile
import shutil
import tempfile

from lxml import etree
from fastapi import HTTPException
from . import binding, orchestration


def acquire_prior(cli, body):
    report=body['report']
    try:
        search=orchestration.find_prior(cli,report['company'],report['period_end'],body.get('report_type','half'))
    except (KeyError,TypeError,ValueError):
        raise HTTPException(422,'회사·보고기간·보고서 종류를 확인하세요') from None
    except Exception:
        raise HTTPException(502,'회사/전기 공시 검색 실패 — 연결과 회사명을 확인하고 재시도하세요') from None
    docs=search['documents']
    selected=body.get('prior_receipt')
    if not docs: raise HTTPException(404,search['message'])
    if not selected and len(docs)>1: raise HTTPException(409,'전기 공시 후보가 여러 개입니다. 보고서명·기간·접수번호를 선택하세요')
    doc=next((d for d in docs if d['rcept_no']==selected),None) if selected else docs[0]
    if doc is None: raise HTTPException(422,'선택한 접수번호가 해당 회사/전기 보고기간의 검색 결과에 없습니다')
    from dart_explorer.xbrl.pipeline import download_xbrl, unpack_xbrl, REPRT, XbrlNotAvailable
    try:
        _,path=download_xbrl(cli,search['corp_code'],doc['rcept_no'],REPRT[doc['report_type']])
        # Validate the archive boundary before the existing extraction routine.
        with zipfile.ZipFile(path) as z:
            if any('..' in Path(n.replace('\\','/')).parts or Path(n).is_absolute() or Path(n).drive for n in z.namelist()):
                raise ValueError('패키지 경로 형식 불지원')
            existing=Path(path).with_suffix('')
            unchanged=existing.is_dir() and all(
                (existing/info.filename).is_file() and (existing/info.filename).read_bytes()==z.read(info)
                for info in z.infolist() if not info.is_dir())
        if unchanged:
            folder=str(existing)
        else:
            # Never let unpack_xbrl overwrite a user's edited cache package.
            isolated=Path(tempfile.mkdtemp(prefix='orchestration_',dir=Path(path).parent))
            archive=isolated/Path(path).name
            shutil.copyfile(path,archive)
            folder=unpack_xbrl(str(archive))
    except XbrlNotAvailable:
        raise HTTPException(404,'선택한 전기 공시에 제출 XBRL이 없습니다. 당기 원천 검토로 계속할 수 있습니다') from None
    except (zipfile.BadZipFile,ValueError):
        raise HTTPException(422,'전기 XBRL package 형식 불지원') from None
    except Exception:
        raise HTTPException(502,'전기 XBRL 다운로드/해제 실패 — 수신 상태와 접수번호를 확인하고 재시도하세요') from None
    try:
        result=package_evidence(folder,report['scope'],search['period'])
    except (OSError,ValueError,IndexError,KeyError,TypeError,AttributeError,etree.XMLSyntaxError):
        raise HTTPException(422,'전기 package의 instance/presentation/기간·범위 구조를 확인할 수 없습니다') from None
    return {**result,'company':report['company'],'scope':report['scope'],'period_end':search['period'],
            'corp_code':search['corp_code'],'receipt':doc['rcept_no'],'report_name':doc['report_nm'],
            'origin':'PRIOR_COMPANY_XBRL'}


def package_evidence(folder, scope, period_end, origin='PRIOR_COMPANY_XBRL'):
    from dart_explorer.xbrl.taxonomy import TaxonomyPackage, LB, XL
    from dart_explorer.xbrl.dimension_table import XbrlInstance
    files=sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in ('.xbrl','.xsd','.xml'))
    if sum(p.suffix.lower()=='.xbrl' for p in files)!=1:
        raise ValueError('단일 instance 패키지가 필요합니다; 여러 instance를 임의 선택하지 않습니다')
    initial_hashes={str(p.resolve()):binding.digest(p.read_bytes()) for p in files}
    package=TaxonomyPackage(folder); instance=XbrlInstance(folder)
    explicit_periods=[]
    for fact in instance.facts.get('dart-gcd_DocumentPeriodEndDate',[]):
        try: explicit_periods.append(date.fromisoformat(fact['value']))
        except ValueError: raise ValueError('보고기말 fact 형식 불지원') from None
    reported_end=max(explicit_periods) if explicit_periods else instance.doc_period_end
    if reported_end is None or reported_end.isoformat()!=period_end:
        raise ValueError('전기 instance 보고기간 불일치')
    parser=etree.XMLParser(resolve_entities=False,no_network=True)
    schemas={};relationships=[];fact_records=[];identifiers=set()
    for path in files:
        root=etree.parse(str(path),parser).getroot()
        if path.suffix.lower()=='.xsd':
            for el in root.iter('{http://www.w3.org/2001/XMLSchema}element'):
                if el.get('id'): schemas[el.get('id')]={'namespace':root.get('targetNamespace'),'schema_id':el.get('id')}
        for link in root:
            if not isinstance(link.tag,str): continue
            if link.tag in (f'{{{LB}}}definitionLink',f'{{{LB}}}calculationLink',f'{{{LB}}}presentationLink'):
                locs={e.get(f'{{{XL}}}label'):e.get(f'{{{XL}}}href') for e in link if e.tag==f'{{{LB}}}loc'}
                for arc in link:
                    if isinstance(arc.tag,str) and arc.tag.endswith('Arc'):
                        relationships.append({'role':link.get(f'{{{XL}}}role'),'arcrole':arc.get(f'{{{XL}}}arcrole'),
                            'from':locs.get(arc.get(f'{{{XL}}}from')),'to':locs.get(arc.get(f'{{{XL}}}to')),
                            'order':arc.get('order'),'weight':arc.get('weight'),'origin':origin})
        if path.suffix.lower()=='.xbrl':
            for el in root.iter('{http://www.xbrl.org/2003/instance}identifier'):
                identifiers.add((el.get('scheme'),el.text))
            for el in root:
                if not isinstance(el.tag,str) or not el.get('contextRef'): continue
                qname=etree.QName(el.tag)
                fact_records.append({'prefix':el.prefix,'name':qname.localname,'namespace':qname.namespace,
                    'context_id':el.get('contextRef'),'unit_ref':el.get('unitRef'),'decimals':el.get('decimals'),
                    'value':el.text,'nil':el.get('{http://www.w3.org/2001/XMLSchema-instance}nil'),
                    'context':instance.contexts.get(el.get('contextRef')),'origin':origin})
    concepts=[]
    for role,definition,pl in package.roles():
        if binding._scope(definition)!=scope: continue
        for row in package.tree_rows(pl):
            eid=row['prefix']+'_'+row['id']; attrs=package.ext_attrs.get(eid,{})
            facts=instance.facts.get(eid,[])
            dimensions=sorted({tuple(sorted(f['ctx']['dims'].items())) for f in facts if f['ctx']['end']==period_end})
            concepts.append({'prefix':row['prefix'],'name':row['id'],'role':role,
                'label_ko':row['ko'],'data_type':binding._type(attrs.get('type')) or None,
                'period':attrs.get('periodType','').upper() or None,
                'dimensions':dimensions if dimensions else None,'depth':row['depth'],
                'contexts':[f['ctx'] for f in facts],'units':sorted({f['unit'] for f in facts}),
                **schemas.get(eid,{'namespace':None,'schema_id':None})})
    if not concepts: raise ValueError('전기 package의 선택 범위 Role 없음')
    paths={str(i):str(p.resolve()) for i,p in enumerate(files)}
    hashes={str(i):binding.digest(p.read_bytes()) for i,p in enumerate(files)}
    if any(hashes[str(i)]!=initial_hashes[str(p.resolve())] for i,p in enumerate(files)):
        raise ValueError('분석 중 XBRL 원천이 변경되었습니다')
    return {'concepts':concepts,'paths':paths,'hashes':hashes,'facts':fact_records,'relationships':relationships,
        'issuer_identifiers':[{'scheme':s,'value':v} for s,v in sorted(identifiers,key=str)],
        'components':{'schema':any(p.suffix=='.xsd' for p in files),
            'label':any('_lab' in p.name for p in files),'presentation':True,
            'definition':any('_def' in p.name for p in files),'calculation':any('_cal' in p.name for p in files)},
        'limitations':['전기 scope 명시 Role만 참고','표준 schema import 자동 해석 없음','typed dimension 재검토 필요']}
