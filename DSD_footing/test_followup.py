"""Owner-reviewed public/synthetic follow-up behaviors; no baseline updates."""
from pathlib import Path
import tempfile
import unittest
import core
import refmap
from types import SimpleNamespace
from test_issue27_30 import draw

class Followup(unittest.TestCase):
    def test_balance_account_categories_preserve_roles(self):
        for label in ['당기손익-공정가치측정금융자산','기타포괄손익-공정가치금융자산','미수수익','선급비용','평가충당금']:
            with self.subTest(label=label):
                self.assertEqual(('잔액','말'),refmap._role(label,'당기말','',tag='BS'))
                self.assertEqual(('잔액','말'),refmap._role(label,'당기말',''))
        self.assertEqual(('거래액',None),refmap._role('유형자산처분손익','당기말',''))

    def test_unbound_single_date_does_not_identify_both_sides(self):
        data=[['구분','당기말','전기말'],['현금','200,000,000','300,000,000'],['기타','400,000,000','500,000,000']]
        ctx=dict(headers=data,scope='',owner=None,dates=('2025-12-31',),anchors={})
        evidence=refmap._cell_evidence(data,ctx,'BS')
        self.assertIsNone(evidence[(1,1)]['period'])
        self.assertIsNone(evidence[(1,2)]['period'])

    def test_equal_different_flows_remain_review(self):
        a=dict(period=('당',None,None,()),role=('거래액',None),label='순확정급여부채의 재측정요소')
        b=dict(period=a['period'],role=a['role'],label='사외적립자산의 수익')
        self.assertFalse(refmap.same_period(a,b))

    def test_supported_continuation_with_same_section_and_layout(self):
        old=[['구분','당기말','전기말'],['현금','200,000,000','300,000,000'],['금융자산','400,000,000','500,000,000']]
        new=[['기타자산','600,000,000','700,000,000'],['합계','1200,000,000','1500,000,000']]
        def table(data):
            return SimpleNamespace(bbox=(20,100,530,200),extract=lambda:data,rows=[SimpleNamespace(cells=[(20,100,200,120),(200,100,365,120),(365,100,530,120)])])
        first=SimpleNamespace(find_tables=lambda:[table(old)],extract_words=lambda:[dict(text='1.',x0=20,x1=30,top=70,bottom=80),dict(text='금융자산',x0=35,x1=100,top=70,bottom=80)])
        second=SimpleNamespace(find_tables=lambda:[table(new)],extract_words=lambda:[])
        ctx=refmap.period_contexts(SimpleNamespace(pages=[first,second]),{(1,1):1,(2,1):1})
        self.assertTrue(ctx[(2,1)]['inherited'])

    def test_ratio_threshold_trap_not_currency(self):
        r=self.pdf_case('1. 비율 (당기말)',['구분','구성비(%)','지분율(%)'],[['A','200','300'],['B','200','300']],note_unit='백만원')
        self.assertEqual(0,len(r[3]))
        self.assertEqual([],r[2])
    def test_ratio_projection_preserves_source_exclusions(self):
        t=[['구분','이전보고금액','수정금액','재작성후금액','구성비(%)'],['A','1000','0','1000','40'],['B','2000','0','2000','60'],['합계','3000','0','3000','100']]
        rs=[r for r in core.check_table(t) if r.get('col')==4]
        self.assertEqual(1,len(rs)); self.assertEqual('SKIP',core.verdict(rs[0]))

    def test_asset_disposal_gains_not_balance(self):
        r=self.pdf_case('1. 유형자산',['구분','당기','전기'],[['유형자산처분손익','200,000,000','300,000,000'],['기타','400,000,000','500,000,000']],main_label='유형자산')
        self.assertEqual(0,len(r[3])); self.assertEqual(2,len(r[4]))
        self.assertTrue(all(m.get('review_candidates') for m,_ in r[4]))

    def test_standalone_dates_are_not_discarded(self):
        data=[['구분','당기말','전기말'],['현금','200,000,000','300,000,000'],['기타','400,000,000','500,000,000']]
        def page(date):
            return SimpleNamespace(find_tables=lambda:[SimpleNamespace(bbox=(20,100,530,200),extract=lambda:data)],extract_words=lambda:[dict(text=date,x0=20,x1=100,top=70,bottom=80)])
        contexts=refmap.period_contexts(SimpleNamespace(pages=[page('2025.12.31'),page('2024.12.31')]),{(1,1):1,(2,1):1})
        a=refmap._cell_evidence(data,contexts[(1,1)],'BS')[(1,1)]
        b=refmap._cell_evidence(data,contexts[(2,1)],'BS')[(1,1)]
        self.assertFalse(refmap.same_period(a,b))
    def test_independent_ownership_rates_remain_review(self):
        t=[['종속기업','지분율(%)'],['자회사A','100'],['자회사B','100'],['합계','200']]
        rs=[r for r in core.check_table(t) if r['kind']=='A1']
        self.assertEqual(1,len(rs)); self.assertEqual('SKIP',core.verdict(rs[0]))

    def test_side_by_side_scope_does_not_leak(self):
        data=[['구분','금액'],['현금','200,000,000'],['기타','300,000,000']]
        table=lambda box: SimpleNamespace(bbox=box,extract=lambda:data)
        page=SimpleNamespace(find_tables=lambda:[table((20,100,250,200)),table((300,100,530,200))],extract_words=lambda:[dict(text='당기말',x0=20,x1=60,top=70,bottom=80)])
        ctx=refmap.period_contexts(SimpleNamespace(pages=[page]),{(1,1):1,(1,2):1})
        self.assertEqual('',ctx[(1,2)]['scope'])

    def test_unrelated_continuation_not_inherited(self):
        old=[['구분','당기말','전기말'],['현금','200,000,000','300,000,000'],['합계','200,000,000','300,000,000']]
        new=[['다른내용','400,000,000','500,000,000'],['기타','600,000,000','700,000,000']]
        page=lambda data: SimpleNamespace(find_tables=lambda:[SimpleNamespace(bbox=(20,100,530,200),extract=lambda:data)],extract_words=lambda:[])
        ctx=refmap.period_contexts(SimpleNamespace(pages=[page(old),page(new)]),{(1,1):1,(2,1):1})
        self.assertFalse(ctx[(2,1)]['inherited'])
    def test_ratio_sum_restored_without_currency_discovery(self):
        t=[['주주','소유주식수','지분율(%)'],['A','1,000','35.68'],['B','2,000','13.19'],['C','3,000','51.13'],['합계','6,000','100']]
        self.assertEqual([1],core.grid_info(t)[-1])
        rs=[r for r in core.check_table(t) if r['kind']=='A1' and r.get('col')==2]
        self.assertEqual(1,len(rs)); self.assertEqual('OK',core.verdict(rs[0]))
        t[-1][2]='103'
        rs=[r for r in core.check_table(t) if r['kind']=='A1' and r.get('col')==2]
        self.assertEqual('DIFF',core.verdict(rs[0],0,1))

    def test_nonadditive_rate_candidate_visible(self):
        t=[['상품','이자율(%)'],['A','10'],['B','20'],['합계','30']]
        rs=[r for r in core.check_table(t) if r['kind']=='A1']
        self.assertEqual(1,len(rs)); self.assertEqual('SKIP',core.verdict(rs[0]))

    def test_category_is_not_period(self):
        t=[['구분','당기손익-공정가치측정 금융자산','합계'],['자산','100,000,000','100,000,000'],['기타','200,000,000','200,000,000']]
        self.assertEqual({},refmap.column_periods(t))

    def test_merged_period_at_excluded_ratio_column(self):
        t=[['회사','당기말',None,None,'전기말',None,None],['','지분율(%)','원가','장부금액','지분율(%)','원가','장부금액'],['A','10','200,000,000','100,000,000','20','300,000,000','200,000,000'],['B','20','300,000,000','200,000,000','30','400,000,000','300,000,000']]
        ps=refmap.column_periods(t)
        self.assertEqual('당',ps[2][0]); self.assertEqual('전',ps[5][0])

    def pdf_case(self,title,headers,rows,main_label='현금및현금성자산',note_unit='원'):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'case.pdf'
            draw(p,[('재무상태표','원',[['과목','주석','당기말','전기말'],[main_label,'1','200,000,000','300,000,000'],['기타자산','','400,000,000','500,000,000']],[200,40,120,120]),(title,note_unit,[headers,*rows],[200,120,120])])
            return refmap.build(str(p))

    def test_external_prior_category_does_not_link_current(self):
        r=self.pdf_case('1. 금융자산 (전기말)',['구분','당기손익-공정가치측정 금융자산','합계'],[['금융자산','200,000,000','200,000,000'],['기타자산','400,000,000','400,000,000']])
        self.assertEqual(0,len(r[3])); self.assertEqual(2,len(r[4]))

    def test_external_current_balance_links(self):
        r=self.pdf_case('1. 금융자산 (당기말)',['구분','상각후원가 금융자산','합계'],[['현금및현금성자산','200,000,000','200,000,000'],['기타자산','400,000,000','400,000,000']])
        self.assertEqual(1,len(r[3])); self.assertEqual(1,len(r[4]))

    def test_rollforward_endpoints_not_acquisitions(self):
        r=self.pdf_case('1. 유형자산 (당기 중 변동)',['구분','금액','합계'],[['기초','300,000,000','300,000,000'],['취득','200,000,000','200,000,000'],['기말','200,000,000','200,000,000']],main_label='유형자산')
        self.assertEqual(1,len(r[3]))
        self.assertEqual({'기말'},{n['label'] for m,cs in r[3] for n in cs})

    def test_scope_header_conflict_stays_review(self):
        r=self.pdf_case('1. 금융자산 (전기말)',['구분','당기말','전기말'],[['현금및현금성자산','200,000,000','300,000,000'],['기타자산','400,000,000','500,000,000']])
        self.assertEqual(1,len(r[3]))
        self.assertEqual('전',r[3][0][0]['period'][0])

if __name__=='__main__': unittest.main()
