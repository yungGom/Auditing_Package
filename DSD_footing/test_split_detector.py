"""분할 의심 탐지기(final.ends_open)가 비율(%) 열만 있는 표도 감시하는지.

final.py는 실행 스크립트라 import하지 않고 함수 정의만 떼어 실행한다
(test_a5_equity.py의 예외색인 테스트와 같은 방식)."""
import ast
from pathlib import Path
import unittest

import core
from core import grid_info, is_total_label

HEADER = ['지역', '기업명', '업종', '지분율(%)']


def ends_open():
    module = ast.parse(Path(__file__).with_name('final.py').read_text(encoding='utf-8'))
    node = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'ends_open')
    scope = dict(grid_info=grid_info, is_total_label=is_total_label, core=core)
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<final.ends_open>', 'exec'), scope)
    return scope['ends_open']


class RatioOnlyTableIsWatched(unittest.TestCase):
    def setUp(self):
        self.ends_open = ends_open()

    def test_ratio_column_was_dropped_from_amount_columns(self):
        # 전제 확인: 이 표에서 금액열은 0개다. 이 전제가 깨지면 아래 테스트가 무의미해진다.
        table = [HEADER, ['미주', 'A Inc.', '판매', '100.0'], ['', 'B Ltd.', '생산', '60.5']]
        self.assertEqual([], grid_info(table)[6])

    def test_ratio_only_table_without_total_is_open(self):
        table = [HEADER, ['미주', 'A Inc.', '판매', '100.0'], ['', 'B Ltd.', '생산', '60.5']]
        self.assertTrue(self.ends_open(table))

    def test_ratio_only_table_ending_in_total_is_closed(self):
        table = [['구분', '주주', '지분율(%)'], ['', '갑', '60.0'], ['', '을', '40.0'], ['', '합계', '100.0']]
        self.assertFalse(self.ends_open(table))

    def test_text_only_table_is_not_watched(self):
        self.assertFalse(self.ends_open([['항목', '설명'], ['안내', '금액표 없음']]))


if __name__ == '__main__':
    unittest.main()
