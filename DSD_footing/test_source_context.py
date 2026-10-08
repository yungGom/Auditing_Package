"""Source identity controls for Issue18 follow-up; synthetic, no baseline edits."""
import unittest
from types import SimpleNamespace
import core
import refmap


class SourceContext(unittest.TestCase):
    def test_invalid_header_date_is_not_rescued(self):
        d=[['구분','당기','2025년2월30일'],['매출','200','200'],['기타수익','100','100']]
        e=refmap._cell_evidence(d,dict(headers=d,scope='',owner=None,anchors={}))
        self.assertIsNone(e[(1,2)]['period'])

    def test_adjusted_investment_closing_total_remains_balance(self):
        d=[['구분','기말장부금액'],['투자A','200'],['합계','200']]
        e=refmap._cell_evidence(d,dict(headers=d,scope='당기말',owner=None,title='한 지분의 장부금액으로 조정한 내역은 다음과 같습니다.'))
        self.assertEqual(('잔액','말'),e[(2,1)]['role'])
        self.assertIsNone(refmap._title_item('한 지분의 장부금액으로 조정한 내역은 다음과 같습니다.'))

    def test_invalid_instant_is_not_period_evidence(self):
        self.assertEqual((),refmap._dates('2025년2월30일'))
        self.assertIsNone(refmap._period('당기말 2025년2월30일'))
        self.assertEqual(('2024-2-29',),refmap._dates('2024년2월29일'))

    def test_revenue_name_does_not_turn_receivable_into_flow(self):
        for label in ('매출채권','장기매출채권','매출채권및기타채권'):
            self.assertEqual(('잔액','말'),refmap._role(label,'당기말',''))
        self.assertEqual(('거래액',None),refmap._role('매출채권처분손익','당기',''))
        for label in ('매출','매출액','매출원가'):
            self.assertEqual(('거래액',None),refmap._role(label,'당기',''))

    def test_new_subsection_clears_current_only_narrative(self):
        d=[['구분','당기말','전기말'],['계약부채','200','300'],['합계','200','300']]
        table=lambda box:SimpleNamespace(bbox=box,extract=lambda:d)
        words=[dict(text='(4) 당기말 현재 계약자산',x0=20,x1=250,top=70,bottom=80),
               dict(text='(5) 당기말 및 전기말 현재 계약부채의 내역',x0=20,x1=400,top=250,bottom=260)]
        page=SimpleNamespace(find_tables=lambda:[table((20,100,530,200)),table((20,300,530,400))],extract_words=lambda:words)
        ctx=refmap.period_contexts(SimpleNamespace(pages=[page]),{(1,1):1,(1,2):1})
        e=refmap._cell_evidence(d,ctx[(1,2)])
        self.assertEqual('전',e[(1,2)]['period'][0])
        self.assertEqual('',ctx[(1,2)]['scope'])

    def test_one_row_donor_and_small_grid_rounding(self):
        old=[['구분','자산A','자산B','합계'],['기초','100','200','300']]
        new=[['취득','10','20','30'],['기말','110','220','330']]
        def table(data,bounds,box):
            return SimpleNamespace(bbox=box,extract=lambda:data,rows=[SimpleNamespace(cells=[(a,box[1],b,box[3]) for a,b in zip(bounds,bounds[1:])])])
        first=SimpleNamespace(find_tables=lambda:[table(old,[20,160,280,400,530],(20,700,530,800))],extract_words=lambda:[dict(text='10. 무형자산',x0=20,x1=150,top=650,bottom=660),dict(text='(1) 당기',x0=20,x1=100,top=670,bottom=680)])
        second=SimpleNamespace(find_tables=lambda:[table(new,[20,161.5,281.5,401.5,530],(20,50,530,150))],extract_words=lambda:[])
        ctx=refmap.period_contexts(SimpleNamespace(pages=[first,second]),{(1,1):1,(2,1):1})
        self.assertTrue(ctx[(2,1)]['inherited'])
        self.assertEqual((1,1),ctx[(2,1)]['donor'])
        e=refmap._cell_evidence(new,ctx[(2,1)])
        self.assertEqual('당',e[(1,3)]['period'][0])
        self.assertEqual(('잔액','말'),e[(1,3)]['role'])
        second.find_tables=lambda:[table(new,[20,170,290,410,530],(20,50,530,150))]
        ctx=refmap.period_contexts(SimpleNamespace(pages=[first,second]),{(1,1):1,(2,1):1})
        self.assertFalse(ctx[(2,1)]['inherited'])

    def test_quarter_ordinal_is_not_three_month_duration(self):
        self.assertEqual('누적',refmap._duration_kind('제6기 3분기',('2025-1-1','2025-9-30')))
        self.assertEqual('3M',refmap._duration_kind('제6기 3분기',('2025-7-1','2025-9-30')))
        self.assertIsNone(refmap._duration_kind('제6기 3분기',('2025-1-1','2025-2-30')))

    def test_side_by_side_title_does_not_leak(self):
        d=[['구분','당기','전기'],['기타항목','200','300'],['합계','200','300']]
        table=lambda box: SimpleNamespace(bbox=box,extract=lambda:d)
        page=SimpleNamespace(find_tables=lambda:[table((20,100,250,200)),table((300,100,530,200))],extract_words=lambda:[dict(text='판매비와관리비',x0=20,x1=120,top=70,bottom=80)])
        contexts=refmap.period_contexts(SimpleNamespace(pages=[page]),{(1,1):1,(1,2):1})
        e=refmap._cell_evidence(d,contexts[(1,2)])
        self.assertEqual('',contexts[(1,2)]['title'])
        self.assertIsNone(e[(2,1)]['item_identity'])

    def test_conflicting_span_is_not_rescued_by_neighbor(self):
        d=[['구분','당기 3개월','당기 3개월 누적'],['매출','200','200'],['계','200','200']]
        e=refmap._cell_evidence(d,dict(headers=d,scope='',owner=None))
        self.assertIsNotNone(e[(1,1)]['period'])
        self.assertIsNone(e[(1,2)]['period'])

    def test_last_group_total_is_not_grand_total(self):
        d=[['구분','당기','전기'],['판매비와관리비','',''],['급여','100','80'],
           ['계','100','80'],['연구개발비','',''],['연구비','200','150'],['계','200','150']]
        e=refmap._cell_evidence(d,dict(headers=d,scope='',owner=None,title='판매비와관리비'))
        self.assertEqual('연구개발비',e[(6,1)]['item_identity'])

    def test_closed_groups_can_feed_explicit_enclosing_total(self):
        d=[['구분','당기','전기'],['판매비와관리비','',''],['급여','100','80'],
           ['소계','100','80'],['경상연구개발비','',''],['연구개발 총지출액','200','150'],['계','300','230']]
        e=refmap._cell_evidence(d,dict(headers=d,scope='',owner=None,title='판매비와관리비'))
        self.assertEqual('판매비와관리비',e[(6,1)]['item_identity'])

    def test_spaced_shareholder_distribution_and_bad_total(self):
        table = [['주 요 주 주', '주식수', '지분율(%)'],
                 ['A', '1000', '35.68'], ['B', '2000', '13.19'],
                 ['C', '3000', '51.13'], ['합계', '6000', '100']]
        ratios = lambda: [r for r in core.check_table(table) if r.get('unit_role') == 'ratio']
        self.assertEqual('OK', core.verdict(ratios()[0]))
        table[-1][-1] = '103'
        self.assertEqual('DIFF', core.verdict(ratios()[0], 0, 1))

    def test_financing_column_precedes_balance_account(self):
        self.assertEqual(('거래액', None), refmap._role('단기차입금', '재무현금흐름', '당기'))
        self.assertEqual(('잔액', '초'), refmap._role('단기차입금', '기 초', '당기'))
        self.assertEqual(('잔액', '말'), refmap._role('단기차입금', '기 말', '당기'))

    def test_bounded_balance_categories_and_actual_gains(self):
        for label in ['수익증권', '상각후원가측정금융자산', '당기손익-공정가치측정금융부채']:
            self.assertEqual(('잔액', '말'), refmap._role(label, '당기말', ''))
        self.assertEqual(('거래액', None), refmap._role('금융자산처분손익', '당기', ''))

    def test_total_groups_do_not_cross(self):
        data = [['구분', '당기', '전기'], ['금융수익', '', ''], ['이자수익', '200', '300'],
                ['합계', '200', '300'], ['금융비용', '', ''], ['이자비용', '200', '300'], ['합계', '200', '300']]
        e = refmap._cell_evidence(data, dict(headers=data, scope='', owner=None, title='금융수익 및 금융비용'))
        self.assertEqual('금융수익', e[(3, 1)]['item_identity'])
        self.assertEqual('금융비용', e[(6, 1)]['item_identity'])

    def test_unknown_total_does_not_gain_identity(self):
        data = [['구분', '당기', '전기'], ['A', '100', '200'], ['합계', '100', '200']]
        e = refmap._cell_evidence(data, dict(headers=data, scope='', owner=None, title=''))
        self.assertIsNone(e[(2, 1)]['item_identity'])

    def test_duration_anchors_do_not_union_instants(self):
        header = [['과목', '제6(당)기 반기', None, '제5(전)기 반기', None],
                  ['', '3개월', '누적', '3개월', '누적'], ['매출', '100,000', '200,000', '300,000', '400,000'], ['매출원가', '50,000', '100,000', '150,000', '200,000']]
        text = ('요약반기손익계산서\n제6기 2분기 2025년4월1일부터 2025년6월30일까지\n'
                '제6기 반기 2025년1월1일부터 2025년6월30일까지\n'
                '제5기 2분기 2024년4월1일부터 2024년6월30일까지\n'
                '제5기 반기 2024년1월1일부터 2024년6월30일까지\n과목')
        page = SimpleNamespace(extract_text=lambda: text, find_tables=lambda: [SimpleNamespace(extract=lambda: header)])
        anchors = refmap._report_anchors(SimpleNamespace(pages=[page]))
        e = refmap._cell_evidence(header, dict(headers=header, scope='', owner=None, anchors=anchors), 'IS')
        self.assertEqual(('2025-4-1', '2025-6-30'), e[(2, 1)]['period'][3])
        self.assertEqual(('2025-1-1', '2025-6-30'), e[(2, 2)]['period'][3])
        self.assertFalse(refmap.same_period(e[(2, 1)], e[(2, 2)]))

    def test_oci_review_has_no_title_alias(self):
        data = [['구분', '당반기', '전반기'], ['평가손익/처분손익', '', ''],
                ['기타포괄손익-공정가치 측정 금융자산', '(7,533)', '213'], ['파생상품', '100,000', '200,000']]
        e = refmap._cell_evidence(data, dict(headers=data, scope='', owner=None))[(2, 1)]
        main = dict(period=e['period'], role=('거래액', None), label='기타포괄손익-공정가치 금융자산 손익')
        self.assertFalse(refmap.same_period(main, dict(e, label=data[2][0])))


if __name__ == '__main__':
    unittest.main()
