"""
DART XBRL 재무수치 추출기  (로컬 실행 전용)
사용법:  python xbrl_extract.py <파일명.xbrl> [출력.xlsx]
 - 같은 폴더의 *_lab-ko.xml(한글 명칭)을 자동으로 찾아 라벨을 붙입니다.
 - 산출 엑셀 2시트:  [재무수치_정리] 계정 x (연결/별도·기간) 피벗,  [전체Fact] 원자료 719건.
필요 패키지:  pip install lxml pandas openpyxl
"""
import sys, os, glob
from lxml import etree

XBRLI='http://www.xbrl.org/2003/instance'; XBRLDI='http://xbrl.org/2006/xbrldi'
XLINK='http://www.w3.org/1999/xlink'; LB='http://www.xbrl.org/2003/linkbase'
ROLE_STD='http://www.xbrl.org/2003/role/label'

def load_labels(folder):
    cand=glob.glob(os.path.join(folder,'*_lab-ko.xml')) or glob.glob(os.path.join(folder,'*lab*ko*.xml'))
    labels={}
    if not cand: return labels
    r=etree.parse(cand[0]).getroot()
    loc,arc,lab={},{},{}
    for e in r.iter('{%s}loc'%LB):
        h=e.get('{%s}href'%XLINK) or ''
        if '#' in h: loc[e.get('{%s}label'%XLINK)]=h.split('#')[-1]
    for e in r.iter('{%s}labelArc'%LB):
        arc.setdefault(e.get('{%s}from'%XLINK),[]).append(e.get('{%s}to'%XLINK))
    for e in r.iter('{%s}label'%LB):
        key=e.get('{%s}label'%XLINK); role=e.get('{%s}role'%XLINK)
        lab[(role==ROLE_STD,key)]=e.text
    for lloc,concept in loc.items():
        for to in arc.get(lloc,[]):
            txt=lab.get((True,to)) or lab.get((False,to))
            if txt and concept not in labels: labels[concept]=txt
    return labels

def parse_contexts(root):
    ctx={}
    for c in root.findall('{%s}context'%XBRLI):
        p=c.find('{%s}period'%XBRLI); inst=p.find('{%s}instant'%XBRLI)
        if inst is not None: ptype,start,end='instant','',inst.text
        else:
            s=p.find('{%s}startDate'%XBRLI); e=p.find('{%s}endDate'%XBRLI)
            ptype,start,end='duration',(s.text if s is not None else ''),(e.text if e is not None else '')
        dims=[(m.get('dimension').split(':')[-1],(m.text or '').split(':')[-1]) for m in c.findall('.//{%s}explicitMember'%XBRLDI)]
        scope=''
        for a,m in dims:
            if 'ConsolidatedMember' in m: scope='연결'
            elif 'SeparateMember' in m: scope='별도'
        odims=[(a,m) for a,m in dims if 'ConsolidatedAndSeparate' not in a]
        ctx[c.get('id')]=dict(ptype=ptype,start=start,end=end,scope=scope,dims=odims)
    return ctx

def parse_units(root):
    u={}
    for x in root.findall('{%s}unit'%XBRLI):
        m=x.find('.//{%s}measure'%XBRLI); u[x.get('id')]=(m.text.split(':')[-1] if m is not None else '')
    return u

def extract(path):
    folder=os.path.dirname(os.path.abspath(path)); root=etree.parse(path).getroot()
    ctx=parse_contexts(root); units=parse_units(root); labels=load_labels(folder)
    rows=[]
    for el in root:
        if not isinstance(el.tag,str): continue
        cref=el.get('contextRef')
        if cref is None: continue
        val=(el.text or '').strip()
        if not val: continue
        qn=etree.QName(el.tag); prefix=el.prefix or ''; local=qn.localname
        c=ctx.get(cref,{}); num=val.lstrip('-').replace('.','',1).isdigit()
        rows.append(dict(한글명칭=labels.get(f'{prefix}_{local}',''),요소ID=f'{prefix}:{local}',
            연결별도=c.get('scope',''),기간구분=c.get('ptype',''),시작일=c.get('start',''),종료일=c.get('end',''),
            차원=';'.join(f'{a}={m}' for a,m in c.get('dims',[])),통화=units.get(el.get('unitRef'),''),
            decimals=el.get('decimals',''),금액=(float(val) if num else None),텍스트값=('' if num else val[:150])))
    return rows

def build_excel(rows,out):
    import pandas as pd
    from openpyxl.styles import Font,PatternFill,Alignment,Border,Side
    df=pd.DataFrame(rows)
    face=df[(df['차원']=='')&(df['금액'].notna())].copy()  # 차원 없는 본문 계정
    piv=None
    if not face.empty:
        face['열']=face['연결별도'].replace('','(구분없음)')+' '+face['종료일'].astype(str)
        piv=face.pivot_table(index=['한글명칭','요소ID'],columns='열',values='금액',aggfunc='first')
        piv=piv.reindex(sorted(piv.columns,reverse=True),axis=1).reset_index()
    with pd.ExcelWriter(out,engine='openpyxl') as w:
        (piv if piv is not None else df).to_excel(w,sheet_name='재무수치_정리',index=False)
        df.to_excel(w,sheet_name='전체Fact',index=False)
    # 서식
    from openpyxl import load_workbook
    wb=load_workbook(out); hdr=PatternFill('solid',start_color='1F4E78')
    hf=Font(name='맑은 고딕',bold=True,color='FFFFFF'); bf=Font(name='맑은 고딕')
    for ws in wb.worksheets:
        ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
        for c in ws[1]:
            c.fill=hdr; c.font=hf; c.alignment=Alignment(horizontal='center',vertical='center')
        for col in ws.columns:
            L=col[0].column_letter; mx=max((len(str(c.value)) for c in col if c.value is not None),default=8)
            ws.column_dimensions[L].width=min(max(mx+2,10),46)
            for c in col[1:]:
                c.font=bf
                if isinstance(c.value,(int,float)): c.number_format='#,##0;(#,##0)'
    wb.save(out)

if __name__=='__main__':
    if len(sys.argv)<2: print(__doc__); sys.exit(1)
    src=sys.argv[1]; out=sys.argv[2] if len(sys.argv)>2 else src.rsplit('.',1)[0]+'_추출.xlsx'
    rows=extract(src); build_excel(rows,out)
    print(f'추출 완료: {len(rows)}건 -> {out}')
