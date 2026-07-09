"""DSD <-> Excel 변환 파이프라인 (v3).

공시/법인 내부 DSD의 contents.xml에서 셀(TD/TH/TE/TU) 오프셋을 기록하며
Excel로 추출하고, 편집된 Excel에서 변경된 셀만 위치 기반으로 역교체한다.

스코프: 재무제표 + 주석 + 표지 (감사보고서 본문 placeholder는 건드리지 않음)
"""

__version__ = "3.0.0"
