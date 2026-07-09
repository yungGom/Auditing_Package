"""dart_explorer — 공개 공시 검색·수집 (OpenDART 수신 전용).

보안 원칙 (지시서 §0):
- 허용: 공개 데이터의 수신 (OpenDART API 다운로드)
- 금지: 고객사 데이터의 송신 (업로드/웹훅/클라우드/텔레메트리 일체)
- API 키는 dart_explorer/.env 로컬 저장, 레포 커밋 금지 (.gitignore)
- dsd_workbench와는 "폴더에 저장된 파일"로만 연결.
  import 방향은 explorer→workbench 단방향만 허용.
"""
__version__ = "0.1.0"
