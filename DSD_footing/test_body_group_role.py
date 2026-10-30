"""Synthetic source-role controls; no accounting equivalence or baseline edits."""
import unittest
import refmap


CATEGORY = '기타포괄손익-공정가치 측정 금융자산'
GROUP = '평가손익/처분손익'


class BodyGroupRole(unittest.TestCase):
    def evidence(self, rows, title='', tag=None, headers=('당반기', '전반기')):
        data = [['구분', *headers], *rows]
        return refmap._cell_evidence(data, dict(headers=data, scope='', owner=None,
                                              title=title), tag)

    def test_explicit_body_group_supplies_flow_and_physical_source(self):
        result = self.evidence([[GROUP, '', ''], [CATEGORY, '1200', '1300'],
                                ['다른 범주', '1400', '1500']])[(2, 1)]
        self.assertEqual(('거래액', None), result['role'])
        self.assertEqual(dict(kind='table_row_group', row=1, label=GROUP),
                         result['role_source'])
        self.assertEqual(refmap._item_key(CATEGORY), result['item_identity'])

    def test_group_role_does_not_establish_oci_equivalence(self):
        note = self.evidence([[GROUP, '', ''], [CATEGORY, '1200', '1300'],
                              ['다른 범주', '1400', '1500']])[(2, 1)]
        main = dict(period=note['period'], role=('거래액', None),
                    item_identity=refmap._item_key('기타포괄손익-공정가치 금융자산 손익'))
        self.assertEqual(('거래액', None), note['role'])
        self.assertFalse(refmap.same_period(main, note))

    def test_spaced_heading_retains_raw_group_source(self):
        raw = '평가 손익 / 처분 손익'
        result = self.evidence([[raw, '', ''], [CATEGORY, '1200', '1300'],
                                ['다른 범주', '1400', '1500']])[(2, 1)]
        self.assertEqual(('거래액', None), result['role'])
        self.assertEqual(raw, result['role_source']['label'])

    def test_title_alone_does_not_supply_body_group(self):
        for title in ('', GROUP, '당반기 중 금융상품 범주별 순손익'):
            with self.subTest(title=title):
                result = self.evidence([[CATEGORY, '1200', '1300'],
                                        ['다른 범주', '1400', '1500']], title)[(1, 1)]
                self.assertIsNone(result['role'])
                self.assertNotIn('role_source', result)

    def test_body_group_ends_at_new_heading_total_or_blank_separator(self):
        for separator in (['장부금액', '', ''], ['합계', '1200', '1300'], ['', '', '']):
            with self.subTest(separator=separator[0]):
                result = self.evidence([[GROUP, '', ''], [CATEGORY, '1200', '1300'],
                                        separator, [CATEGORY, '1400', '1500']])[(4, 1)]
                self.assertIsNone(result['role'])
                self.assertNotIn('role_source', result)

    def test_numeric_or_mixed_heading_does_not_own_group(self):
        for heading in ([GROUP, '2000', '3000'], [GROUP, '장부금액', ''],
                        ['이자수익/처분손익', '', '']):
            with self.subTest(heading=heading):
                result = self.evidence([heading, [CATEGORY, '1200', '1300'],
                                        ['다른 범주', '1400', '1500']])[(2, 1)]
                self.assertIsNone(result['role'])

    def test_explicit_balance_role_is_not_overridden(self):
        result = self.evidence([[GROUP, '', ''], [CATEGORY, '1200', '1300'],
                                ['다른 범주', '1400', '1500']],
                               headers=('당반기말', '전기말'))[(2, 1)]
        self.assertEqual(('잔액', '말'), result['role'])
        self.assertNotIn('role_source', result)

    def test_equity_statement_review_role_is_not_overridden(self):
        result = self.evidence([[GROUP, '', ''], [CATEGORY, '1200', '1300'],
                                ['다른 범주', '1400', '1500']], tag='SCE')[(2, 1)]
        self.assertIsNone(result['role'])
        self.assertNotIn('role_source', result)


if __name__ == '__main__':
    unittest.main()
