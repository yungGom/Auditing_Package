"""Windows launcher must preserve the engine result, including after pause."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


@unittest.skipUnless(sys.platform == 'win32', 'Windows batch launcher')
class BatchExitStatus(unittest.TestCase):
    def run_batch(self, arguments, no_pause):
        env = os.environ.copy()
        env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env.get('PATH', '')
        env['PYTHONIOENCODING'] = 'utf-8'
        env.pop('FOOT_NOPAUSE', None)
        if no_pause:
            env['FOOT_NOPAUSE'] = '1'
        return subprocess.run(
            ['cmd.exe', '/d', '/c', str(ROOT/'run.bat'), *arguments],
            cwd=ROOT, env=env, input='\n', capture_output=True,
            text=True, encoding='utf-8', errors='replace', timeout=90)

    def test_missing_input_keeps_usage_exit(self):
        self.assertEqual(2, self.run_batch([], True).returncode)

    def test_engine_failure_survives_both_pause_modes(self):
        with tempfile.TemporaryDirectory(prefix='batch input ') as directory:
            missing = str(Path(directory)/'missing report.pdf')
            for no_pause in (True, False):
                with self.subTest(no_pause=no_pause):
                    result = self.run_batch([missing], no_pause)
                    self.assertIn('파일이 없습니다', result.stdout)
                    self.assertEqual(2, result.returncode, result.stdout+result.stderr)

    def test_limited_zero_check_run_still_returns_success(self):
        from test_issue27_30 import draw
        with tempfile.TemporaryDirectory(prefix='batch input ') as directory:
            source = Path(directory)/'zero checks.pdf'
            draw(source, [('합성 자료', '원', [['항목','설명'],['안내','금액표 없음']], [200,250])])
            result = self.run_batch([str(source)], False)
            self.assertEqual(0, result.returncode, result.stdout+result.stderr)
            self.assertIn('산술검사 0건', result.stdout)
            self.assertTrue((source.parent/'zero checks_틱마크.pdf').is_file())
            self.assertTrue((source.parent/'zero checks_예외색인.xlsx').is_file())


if __name__ == '__main__':
    unittest.main()
