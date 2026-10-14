"""Synthetic controls for the Owner-approved single PBT equity-method rule."""
import ast
from pathlib import Path
import unittest

from core import verdict
from statements import foot_a5

TARGET = '법인세비용차감전순이익'


def table(equity=(), totals=(122000000, 122000000), headers=('당기', '전기'), after=()):
    def repeated(value):
        return [str(value)] * len(headers)
    return [['과목', *headers], ['영업이익', *repeated(100000000)],
            ['기타수익', *repeated(20000000)], ['기타비용', *repeated(5000000)],
            ['금융수익', *repeated(10000000)], ['금융비용', *repeated(3000000)],
            *[[label, *['' if value is None else str(value) for value in values]]
              for label, values in equity],
            [TARGET, *['' if value is None else str(value) for value in totals]], *after]


class EquityMethodPBT(unittest.TestCase):
    def results(self, source):
        return [r for r in foot_a5(source) if r['label'] == TARGET]

    def assert_calculated(self, source, expected):
        results = self.results(source)
        self.assertEqual(len(expected), len(results))
        for result, amount in zip(results, expected):
            self.assertGreater(result['n'], 0)
            self.assertEqual(amount, result['calc'])
            self.assertEqual('OK', verdict(result))
        return results

    def assert_unknown(self, source):
        results = self.results(source)
        self.assertTrue(results)
        for result in results:
            self.assertEqual('SKIP', verdict(result))
            self.assertEqual(0, result['n'])
            self.assertIsNone(result['calc'])
            self.assertTrue(result['reason'])
            self.assertTrue(result['reason_text'])
            self.assertIn('source_rows', result)
        return results

    def test_signed_net_profit_is_included_once(self):
        self.assert_calculated(table([('지분법손익', (7000000, 7000000))],
                                     (129000000, 129000000)), [129000000, 129000000])

    def test_signed_net_loss_is_not_absolute_value(self):
        self.assert_calculated(table([('지분법손익', (-7000000, -7000000))],
                                     (115000000, 115000000)), [115000000, 115000000])

    def test_parenthesized_net_label_preserves_sign(self):
        self.assert_calculated(table([('지분법이익(손실)', (7000000, -7000000))],
                                     (129000000, 115000000)), [129000000, 115000000])

    def test_explicit_zero_is_known(self):
        self.assert_calculated(table([('지분법손익', (0, 0))]), [122000000, 122000000])

    def test_absent_equity_preserves_five_terms(self):
        results = self.assert_calculated(table(), [122000000, 122000000])
        self.assertTrue(all(r['n'] == 5 for r in results))

    def test_separate_nonnegative_gain_and_loss(self):
        self.assert_calculated(table([('지분법이익', (7000000, 7000000)),
                                      ('지분법손실', (3000000, 3000000))],
                                     (126000000, 126000000)), [126000000, 126000000])

    def test_nonnegative_gain_only(self):
        self.assert_calculated(table([('지분법이익', (7000000, 7000000))],
                                     (129000000, 129000000)), [129000000, 129000000])

    def test_nonnegative_loss_only(self):
        self.assert_calculated(table([('지분법손실', (7000000, 7000000))],
                                     (115000000, 115000000)), [115000000, 115000000])

    def test_negative_split_loss_is_unconfirmed(self):
        self.assert_unknown(table([('지분법손실', (-7000000, -7000000))]))

    def test_negative_split_gain_is_unconfirmed(self):
        self.assert_unknown(table([('지분법이익', (-7000000, -7000000))]))

    def test_net_plus_split_does_not_double_count(self):
        self.assert_unknown(table([('지분법손익', (7000000, 7000000)),
                                   ('지분법이익', (7000000, 7000000))]))

    def test_equal_duplicate_net_is_not_absorbed(self):
        self.assert_unknown(table([('지분법손익', (7000000, 7000000)),
                                   ('지분법손익', (7000000, 7000000))]))

    def test_equal_duplicate_gain_is_not_absorbed(self):
        self.assert_unknown(table([('지분법이익', (7000000, 7000000)),
                                   ('지분법이익', (7000000, 7000000))]))

    def test_duplicate_loss_is_unconfirmed(self):
        self.assert_unknown(table([('지분법손실', (7000000, 7000000)),
                                   ('지분법손실', (7000000, 7000000))]))

    def test_blank_duplicate_net_is_not_discarded(self):
        self.assert_unknown(table([('지분법손익', (7000000, 7000000)),
                                   ('지분법손익', (None, None))]))

    def test_both_period_equity_blank_is_not_absent_zero(self):
        self.assert_unknown(table([('지분법손익', (None, None))]))

    def test_all_blank_loss_with_gain_is_not_zero(self):
        self.assert_unknown(table([('지분법이익', (7000000, 7000000)),
                                   ('지분법손실', (None, None))]))

    def test_question_mark_is_unknown(self):
        self.assert_unknown(table([('지분법손익', ('?', '?'))]))

    def test_dash_is_missing_not_zero(self):
        self.assert_unknown(table([('지분법손익', ('-', '-'))]))

    def test_missing_current_does_not_borrow_prior(self):
        results = self.results(table([('지분법손익', (None, 7000000))],
                                     (122000000, 129000000)))
        self.assertEqual(2, len(results))
        self.assertEqual('SKIP', verdict(results[0]))
        self.assertIsNone(results[0]['calc'])
        self.assertEqual(129000000, results[1]['calc'])
        self.assertEqual('OK', verdict(results[1]))

    def test_four_periods_do_not_leak(self):
        values = (7000000, -7000000, 13000000, -13000000)
        expected = (129000000, 115000000, 135000000, 109000000)
        self.assert_calculated(table([('지분법손익', values)], expected,
                                     ('당기3개월', '당기누적', '전기3개월', '전기누적')),
                               expected)

    def test_period_order_is_source_header_order(self):
        self.assert_calculated(table([('지분법손익', (-7000000, 7000000))],
                                     (115000000, 129000000), ('전기', '당기')),
                               [115000000, 129000000])

    def test_unlabeled_periods_are_unconfirmed(self):
        self.assert_unknown(table([('지분법손익', (7000000, 7000000))],
                                  headers=('금액1', '금액2')))

    def test_duplicate_period_headers_are_unconfirmed(self):
        self.assert_unknown(table([('지분법손익', (7000000, 7000000))],
                                  headers=('당기', '당기')))

    def test_conflicting_current_prior_header_is_unconfirmed(self):
        results = self.results(table([('지분법손익', (7000000, 7000000))],
                                     (122000000, 129000000), ('당기/전기', '전기')))
        self.assertEqual('SKIP', verdict(results[0]))
        self.assertIsNone(results[0]['calc'])
        self.assertEqual('OK', verdict(results[1]))
        self.assertEqual(129000000, results[1]['calc'])

    def test_conflicting_three_month_cumulative_header_is_unconfirmed(self):
        results = self.results(table([('지분법손익', (7000000, 7000000))],
                                     (122000000, 129000000), ('당기3개월누적', '전기')))
        self.assertEqual('SKIP', verdict(results[0]))
        self.assertIsNone(results[0]['calc'])
        self.assertEqual('OK', verdict(results[1]))
        self.assertEqual(129000000, results[1]['calc'])

    def test_oci_after_target_is_not_a_pbt_term(self):
        self.assert_calculated(table(after=[['기타포괄손익-지분법손익', '99000000', '99000000']]),
                               [122000000, 122000000])

    def test_oci_inside_target_span_is_unconfirmed(self):
        self.assert_unknown(table([('기타포괄손익-지분법손익', (99000000, 99000000))]))

    def test_other_unexplained_row_is_not_silent_ok(self):
        self.assert_unknown(table([('다른영업외손익', (7000000, 7000000))]))

    def test_reverse_net_label_is_not_guessed(self):
        self.assert_unknown(table([('지분법손실(이익)', (7000000, -7000000))]))

    def test_unlabeled_amount_is_unconfirmed(self):
        self.assert_unknown(table([('', (7000000, 7000000))]))

    def test_unlabeled_question_mark_is_unconfirmed(self):
        self.assert_unknown(table([('', ('?', '?'))]))

    def test_unlabeled_prior_amount_does_not_borrow(self):
        self.assert_unknown(table([('', (None, 7000000))]))

    def test_true_blank_spacer_is_ignored(self):
        self.assert_calculated(table([('', (None, None))]), [122000000, 122000000])

    def test_blank_duplicate_base_is_unconfirmed(self):
        self.assert_unknown(table([('기타수익', (None, None))]))

    def test_duplicate_base_with_value_is_unconfirmed(self):
        self.assert_unknown(table([('기타수익', (20000000, 20000000))]))

    def test_blank_duplicate_target_is_unconfirmed(self):
        self.assert_unknown(table(after=[[TARGET, '', '']]))

    def test_duplicate_target_with_value_is_unconfirmed(self):
        self.assert_unknown(table(after=[[TARGET, '122000000', '122000000']]))

    def test_missing_base_is_not_partial_calculation(self):
        source = table([('지분법손익', (7000000, 7000000))])
        source[3] = ['기타비용', '', '']
        self.assert_unknown(source)

    def test_reversed_operating_target_order_is_unconfirmed(self):
        source = table()
        source[1], source[-1] = source[-1], source[1]
        self.assert_unknown(source)

    def test_explicit_base_inclusion_does_not_add_twice(self):
        source = table([('지분법손익', (7000000, 7000000))])
        source[2][0] = '기타수익(지분법손익포함)'
        self.assert_unknown(source)

    def test_a_real_arithmetic_difference_remains_diff(self):
        results = self.results(table([('지분법손익', (7000000, 7000000))],
                                     (128000000, 128000000)))
        self.assertTrue(all(r['calc'] == 129000000 for r in results))
        self.assertTrue(all(verdict(r) == 'DIFF' for r in results))

    def test_component_coordinates_and_signs_are_preserved(self):
        results = self.assert_calculated(table([('지분법이익', (7000000, 7000000)),
                                                ('지분법손실', (3000000, 3000000))],
                                               (126000000, 126000000)), [126000000, 126000000])
        for period, result in enumerate(results):
            equity = result['operands'][-2:]
            self.assertEqual([6, 7], [r['row'] for r in equity])
            self.assertEqual([period + 1, period + 1], [r['col'] for r in equity])
            self.assertEqual([1, -1], [r['sign'] for r in equity])


class ExceptionIndexUnknown(unittest.TestCase):
    def test_unknown_calculation_and_delta_stay_blank_with_reason(self):
        module = ast.parse(Path(__file__).with_name('final.py').read_text(encoding='utf-8'))
        block = next(n for n in ast.walk(module) if isinstance(n, ast.If)
                     and isinstance(n.test, ast.Compare)
                     and isinstance(n.test.left, ast.Name) and n.test.left.id == 'v'
                     and any(isinstance(c, ast.Constant) and c.value == 'SKIP'
                             for c in ast.walk(n.test)))
        code = compile(ast.fix_missing_locations(ast.Module(body=[block], type_ignores=[])),
                       '<actual final.py exception output>', 'exec')
        result = {'kind':'A5', 'label':TARGET, 'disp':122000000, 'calc':None, 'n':0,
                  'reason':'EQUITY_VALUE_MISSING', 'reason_text':'이 기간의 지분법손익 금액이 없습니다.'}
        state = dict(v='SKIP', r=result, pi=1, ti=1, unit='원', TUNIT={}, exc=[])
        exec(code, state)
        row = state['exc'][0]
        self.assertIsNone(row[6])
        self.assertIsNone(row[7])
        self.assertEqual('미검증', row[9])
        self.assertEqual(result['reason_text'], row[10])


if __name__ == '__main__':
    unittest.main()
