# -*- coding: utf-8 -*-
"""foot — DSD 풋팅 CLI 진입점. 인자는 final.py와 동일.

사용:
  python foot.py "C:\\감사\\회사\\감사보고서.pdf"
      → 입력 PDF와 같은 폴더에 <원본이름>_틱마크.pdf / <원본이름>_예외색인.xlsx
  python foot.py 보고서.pdf --tol 1 --out D:\\조서\\FA
  python foot.py 보고서.pdf --round-steps 1 --min-won 100000000 --quiet
"""
import os, runpy, sys

sys.argv[0] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "final.py")
sys.path.insert(0, os.path.dirname(sys.argv[0]))
runpy.run_path(sys.argv[0], run_name="__main__")
