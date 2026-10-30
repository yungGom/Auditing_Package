"""세전이익 미검증 사유에 행 이름이 실리는지 — 판정·사유 코드는 바뀌지 않는다(결정 23)."""
import unittest

from core import verdict
from statements import foot_a5
from test_a5_equity import TARGET, table


def pbt(source):
    return [r for r in foot_a5(source) if r['label'] == TARGET]


class ReasonDetailNamesRows(unittest.TestCase):
    def assert_detail(self, source, reason, *names):
        results = pbt(source)
        self.assertTrue(results)
        for r in results:
            self.assertEqual('SKIP', verdict(r))
            self.assertIsNone(r['calc'])
            self.assertEqual(reason, r['reason'])
            for name in names:
                self.assertIn(name, r['reason_detail'])

    def test_missing_anchor_names_every_missing_term(self):
        source = table()
        source[1][0] = '영업손실'
        source[2][0] = '기타영업외수익'
        self.assert_detail(source, 'ANCHOR_AMBIGUOUS', '영업이익(없음)', '기타수익(없음)')

    def test_missing_base_names_the_term(self):
        source = table()
        source[5][0] = '금융원가'
        self.assert_detail(source, 'BASE_MISSING_OR_DUPLICATED', '금융비용(없음)')

    def test_duplicate_base_names_the_count(self):
        self.assert_detail(table([('기타수익', (1, 1))]), 'BASE_MISSING_OR_DUPLICATED', '기타수익(2개)')

    def test_unsupported_row_names_the_row(self):
        self.assert_detail(table([('다른영업외손익', (7000000, 7000000))]),
                           'UNSUPPORTED_SOURCE_ROW', '다른영업외손익')

    def test_unlabeled_row_names_its_position(self):
        self.assert_detail(table([('', (7000000, 7000000))]), 'UNKNOWN_SOURCE_ROW', '라벨 없는 행')

    def test_calculated_result_has_no_detail(self):
        for r in pbt(table([('지분법손익', (7000000, 7000000))], (129000000, 129000000))):
            self.assertEqual('OK', verdict(r))
            self.assertNotIn('reason_detail', r)


if __name__ == '__main__':
    unittest.main()
