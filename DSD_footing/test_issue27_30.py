"""Synthetic regressions for Issues 27–30; no client material."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from openpyxl import load_workbook

import core
import refmap
import tieout

ROOT = Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('IssueSynthetic', r'C:\Windows\Fonts\malgun.ttf'))

def draw(path, specs):
    c = canvas.Canvas(str(path), invariant=1)
    for title, unit, rows, widths in specs:
        c.setFont('IssueSynthetic', 12)
        c.drawString(45, 800, title)
        if unit:
            c.setFont('IssueSynthetic', 9)
            c.drawString(45, 778, f'(단위: {unit})')
        xs = [45]
        for width in widths:
            xs.append(xs[-1]+width)
        for i in range(len(rows)+1):
            c.line(xs[0], 745-i*25, xs[-1], 745-i*25)
        for x in xs:
            c.line(x, 745, x, 745-len(rows)*25)
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                c.drawString(xs[j]+5, 728-i*25, str(value))
        for i in range(4):
            c.drawString(45, 440-i*18, '이 문서는 공개 수치와 무관한 합성 테스트 자료입니다. 실제 고객 자료가 아닙니다.')
        c.showPage()
    c.save()

def b_pdf(path, bs, bu, cf, cu):
    draw(path, [
        ('재무상태표',bu,[['과목','당기','전기'],['현금및현금성자산',bs,bs],['기타자산','2,000','2,000'],['자산총계','3,000','3,000'],['부채와자본총계','3,000','3,000']],[270,100,100]),
        ('현금흐름표',cu,[['과목','당기','전기'],['기초의현금및현금성자산',cf,cf],['현금및현금성자산의증가','0','0'],['기말의현금및현금성자산',cf,cf]],[270,100,100])])

def c_pdf(path, note_values, headers=('당기','전기')):
    draw(path,[
        ('재무상태표','원',[['과목','주석','당기','전기'],['현금및현금성자산','1','100,000,000','200,000,000'],['기타자산','','300,000,000','400,000,000']],[200,50,120,120]),
        ('1. 현금및현금성자산','원',[['구분',*headers],['현금및현금성자산',*note_values],['기타예금','300,000,000','400,000,000']],[250,120,120])])

class AmountColumns(unittest.TestCase):
    def test_small_amount_diff(self):
        t=[['항목','당기'],['상품','10'],['제품','20'],['합계','40']]
        self.assertEqual([1],core.grid_info(t)[-1])
        rows=[r for r in core.check_table(t) if r['kind']=='A1']
        self.assertEqual(1,len(rows))
        self.assertEqual('DIFF',core.verdict(rows[0]))
    def test_small_amount_ok(self):
        t=[['항목','당기'],['상품','10'],['제품','20'],['합계','30']]
        self.assertEqual('OK',core.verdict(core.check_table(t)[0]))
    def test_non_amount_headers(self):
        for h in ['주석','비고','참조','Note','Ref','연번','번호','이자율(%)','이자율']:
            with self.subTest(header=h):
                t=[['항목',h],['상품','10'],['제품','20'],['합계','40']]
                self.assertEqual([],core.grid_info(t)[-1])
    def test_percentage_scenario_headers_are_amounts(self):
        for h in ['10% 상승시','10% 하락시','0.25% 증가','0.25% 감소']:
            with self.subTest(header=h):
                t=[['항목',h],['상품','1,000'],['제품','2,000'],['합계','3,000']]
                self.assertEqual([1],core.grid_info(t)[-1])

class Units(unittest.TestCase):
    def test_unprocessed_second_table_is_not_carried_as_first_unit(self):
        first=[['과목','당기','전기'],['자산총계','1,000','1,000'],['기타자산','2,000','2,000']]
        second=[['과목','당기','전기'],['다른표','10','20'],['다른계','30','40']]
        continuation=[['부채총계','50','60'],['자본총계','70','80']]
        page1=Mock();page1.extract_text.return_value='재무상태표\n과목'
        page1.extract_tables.return_value=[first,second]
        page1.find_tables.return_value=[Mock(bbox=(0,100,500,170)),Mock(bbox=(0,200,500,270))]
        page1.search.return_value=[{'top':80,'groups':('원',)},{'top':180,'groups':('천원',)}]
        page2=Mock();page2.extract_text.return_value='다음 페이지'
        page2.extract_tables.return_value=[continuation]
        page2.find_tables.return_value=[Mock(bbox=(0,100,500,170))]
        page2.search.return_value=[]
        pdf=Mock(pages=[page1,page2]);context=Mock()
        context.__enter__=Mock(return_value=pdf);context.__exit__=Mock(return_value=False)
        with patch.object(tieout.pdfplumber,'open',return_value=context):
            book,*_=tieout.collect('synthetic-mock.pdf')
        self.assertNotIn('부채총계',book['BS'])
        self.assertNotIn('다른표',book['BS'])

    def test_b8_unit_cases(self):
        cases=[('1,000','원','1,000','천원','차이'),('1,000,000','원','1,000','천원','OK'),('1','백만원','1,000','천원','OK'),('1,000','원','1,000','원','OK'),('1,000',None,'1,000','원','미검증'),('1,000','원','1,000',None,'미검증'),('1,000','원/USD','1,000','원','미검증')]
        with tempfile.TemporaryDirectory() as td:
            for i,(bs,bu,cf,cu,v) in enumerate(cases):
                with self.subTest(case=i):
                    path=Path(td)/f'{i}.pdf'; b_pdf(path,bs,bu,cf,cu)
                    b8=[r for r in tieout.run(str(path))[0] if r[0]=='B8']
                    self.assertEqual([v,v],[r[4] for r in b8])

class Periods(unittest.TestCase):
    def test_explicit_period_identity_and_ambiguity(self):
        for a,b in [('당기 2026년','당기 2025년'),('당반기','당분기'),('당기 3개월','당기 3개월 누적'),('당기 2026.06.30','당기 2026.03.31')]:
            with self.subTest(main=a,note=b):
                left=[['과목',a,'전기'],['현금','100,000,000','200,000,000'],['자산','300,000,000','400,000,000']]
                right=[['과목',b,'전기'],['현금','100,000,000','200,000,000'],['자산','300,000,000','400,000,000']]
                self.assertFalse(refmap.same_period({'period':refmap.column_periods(left).get(1)},{'period':refmap.column_periods(right).get(1)}))
    def test_swapped_periods(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'swap.pdf'; c_pdf(p,['200,000,000','100,000,000'])
            r=refmap.build(str(p)); self.assertEqual(0,len(r[3])); self.assertEqual(2,len(r[4]))
    def test_correct_periods(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'correct.pdf'; c_pdf(p,['100,000,000','200,000,000'])
            r=refmap.build(str(p)); self.assertEqual(2,len(r[3])); self.assertEqual(0,len(r[4]))
    def test_unknown_periods(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'unknown.pdf'; c_pdf(p,['100,000,000','200,000,000'],('금액','금액'))
            r=refmap.build(str(p)); self.assertEqual(0,len(r[3])); self.assertEqual(2,len(r[4]))

class ZeroChecks(unittest.TestCase):
    def test_zero_cli_and_quiet(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'zero.pdf'
            draw(p,[('합성 자료','원',[['항목','설명'],['안내','금액표 없음']],[200,250])])
            env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
            for args in ([],['--quiet']):
                r=subprocess.run([sys.executable,'-B',str(ROOT/'foot.py'),str(p),*args],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(0,r.returncode,r.stderr)
                self.assertIn('산술검사 0건',r.stdout)
                wb=load_workbook(Path(td)/'zero_예외색인.xlsx',read_only=True)
                rows=dict(wb['요약'].values)
                self.assertEqual(0,rows['A 산술검증 총건수'])
                self.assertEqual('제한된 분석: 산술검사 0건',rows['분석 상태'])
                wb.close()

if __name__=='__main__':
    unittest.main()
