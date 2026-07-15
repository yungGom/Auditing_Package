"""주식회사 한빛정밀(FICTIONAL) — 실제 DSD 뼈대 + 값 교체 방식 생성기.

from scratch 생성은 dart4.xsd 스키마 위반으로 DART에서 열리지 않았음.
확립 원칙(위치 기반 값 교체)대로:

  뼈대: fixtures/real/삼성전자 별도 (FS 5종 + 주석 32개, 한빛과 동일 5종 구조)
  1) extract --keep-note-numbers → 2) openpyxl로 전 셀 값을 한빛 데이터로 교체
  3) repack --keep-note-numbers --keep-cr → 한빛정밀_오염.dsd
     (뼈대의 "N. N." 헤더 오염 + &cr;-only 319개 그대로 = V8/V5)
  4) 오염본을 기본 extract→repack 통과 → 한빛정밀_클린.dsd (정리 기능 통과분)

뼈대의 행/열/주석 32개 구조는 그대로 사용: 한빛 주석 1~25 매핑,
26~32는 제목만 "(여백)"으로 교체. 남는 데이터 행/셀은 공란 처리.

한계(도구 설계상 서술문 일부는 읽기전용): 주석 헤더 P의 SPAN 뒤 본문과
마크업 포함 문단은 교체되지 않아 뼈대 서술문이 일부 남는다.
"""
import collections
import os
import tempfile

from openpyxl import load_workbook

from ..excel_out import extract
from ..repack import repack

SYN_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "synthetic"))
SKELETON = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "real",
    "[삼성전자(주)]_2025_[감사보고서].dsd"))

COMPANY = "주식회사 한빛정밀"


def _val(v):
    """셀 기록값: 음수는 괄호 문자열(입력 표기 유지), 양수는 숫자."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return f"({abs(v):,})" if v < 0 else v


# ---------------------------------------------------------------------------
# 한빛정밀 데이터 (한빛정밀_검증데이터셋.md, V10 대사 보정 2건 반영)
# kind: item=개별(왼쪽 열), sub=소계(오른쪽 열), label=과목만
# ---------------------------------------------------------------------------

BS_ROWS = [
    ("자          산", "", None, None, "label"),
    ("Ⅰ. 유동자산", "", 66760, 58140, "sub"),
    ("1. 현금및현금성자산", "5", 15230, 12480, "item"),
    ("2. 매출채권", "6, 23", 28450, 25120, "item"),
    ("3. 재고자산", "7", 19870, 17650, "item"),
    ("4. 기타유동자산", "", 3210, 2890, "item"),
    ("Ⅱ. 비유동자산", "", 60140, 56030, "sub"),
    ("1. 유형자산", "8, 10", 52010, 48760, "item"),
    ("2. 무형자산", "9", 4120, 3980, "item"),
    ("3. 이연법인세자산", "19", 2150, 1870, "item"),
    ("4. 기타비유동자산", "", 1860, 1420, "item"),
    ("자산총계", "", 126900, 114170, "sub"),
    ("부          채", "", None, None, "label"),
    ("Ⅰ. 유동부채", "", 37240, 33150, "sub"),
    ("1. 매입채무", "21, 23", 18340, 16780, "item"),
    ("2. 단기차입금", "11", 12000, 10500, "item"),
    ("3. 미지급금", "", 4560, 3980, "item"),
    ("4. 당기법인세부채", "19", 2340, 1890, "item"),
    ("Ⅱ. 비유동부채", "", 25230, 27100, "sub"),
    ("1. 장기차입금", "11", 15000, 18000, "item"),
    ("2. 순확정급여부채", "12", 6780, 6120, "item"),
    ("3. 리스부채", "10", 3450, 2980, "item"),
    ("부채총계", "", 62470, 60250, "sub"),
    ("자          본", "", None, None, "label"),
    ("Ⅰ. 자본금", "13", 10000, 10000, "sub"),
    ("Ⅱ. 주식발행초과금", "13", 8500, 8500, "sub"),
    ("Ⅲ. 이익잉여금", "14", 45930, 35420, "sub"),
    ("자본총계", "", 64430, 53920, "sub"),
    ("부채와자본총계", "", 126900, 114170, "sub"),
]

PL_ROWS = [
    ("Ⅰ. 매출액", "15, 21", 158420, 142350, "sub"),
    ("Ⅱ. 매출원가", "16", 118760, 108240, "sub"),
    ("Ⅲ. 매출총이익", "", 39660, 34110, "sub"),
    ("판매비와관리비", "16", 22340, 20150, "item"),
    ("Ⅳ. 영업이익", "", 17320, 13960, "sub"),
    ("기타수익", "17", 1240, 980, "item"),
    ("기타비용", "17", 560, 720, "item"),
    ("금융수익", "18", 890, 640, "item"),
    ("금융비용", "18", 1450, 1680, "item"),
    ("Ⅴ. 법인세비용차감전순이익", "", 17440, 13180, "sub"),
    ("법인세비용", "19", 4180, 3240, "item"),
    ("Ⅵ. 당기순이익", "", 13260, 9940, "sub"),
    ("Ⅶ. 주당이익", "20", None, None, "label"),
    ("기본주당이익(단위 : 원)", "", 6630, 4970, "item"),
]

PL1_ROWS = [
    ("Ⅰ. 당기순이익", "", 13260, 9940, "sub"),
    ("Ⅱ. 기타포괄손익", "", -250, 180, "sub"),
    ("후속적으로 당기손익으로 재분류되지 않는 항목:", "", None, None, "label"),
    ("순확정급여부채의 재측정요소", "12", -250, 180, "item"),
    ("Ⅲ. 총포괄이익", "", 13010, 10120, "sub"),
]

CF_ROWS = [
    ("Ⅰ. 영업활동현금흐름", "", 17830, 14210, "sub"),
    ("1. 법인세비용차감전순이익", "", 17440, 13180, "item"),
    ("2. 조정", "24", 8290, 7650, "item"),
    ("3. 운전자본의 변동", "24", -3640, -2870, "item"),
    ("4. 이자수취", "", 850, 610, "item"),
    ("5. 이자지급", "", -1380, -1590, "item"),
    ("6. 법인세납부", "", -3730, -2770, "item"),
    ("Ⅱ. 투자활동현금흐름", "", -10100, -8940, "sub"),
    ("1. 유형자산의 취득", "8", -9820, -8650, "item"),
    ("2. 유형자산의 처분", "", 340, 120, "item"),
    ("3. 무형자산의 취득", "9", -620, -410, "item"),
    ("Ⅲ. 재무활동현금흐름", "", -4980, -3180, "sub"),
    ("1. 단기차입금의 순증감", "", 1500, 2000, "item"),
    ("2. 장기차입금의 상환", "", -3000, -1800, "item"),
    ("3. 배당금의 지급", "14", -2500, -2500, "item"),
    ("4. 리스부채의 상환", "10", -980, -880, "item"),
    ("Ⅳ. 현금및현금성자산의 증가", "", 2750, 2090, "sub"),
    ("Ⅴ. 기초 현금및현금성자산", "", 12480, 10390, "sub"),
    ("Ⅵ. 기말 현금및현금성자산", "5", 15230, 12480, "sub"),
]

# CE: 뼈대 열 = 과목/주석/자본금/주식발행초과금(두줄)/이익잉여금/기타자본항목/총계
CE_ROWS = [
    ("2024.1.1(전기초)", "", 10000, 8500, 27800, "-", 46300),
    ("1. 당기순이익", "", "-", "-", 9940, "-", 9940),
    ("2. 순확정급여부채의 재측정요소", "12", "-", "-", 180, "-", 180),
    ("3. 연차배당", "14", "-", "-", -2500, "-", -2500),
    ("2024.12.31(전기말)", "", 10000, 8500, 35420, "-", 53920),
    ("2025.1.1(당기초)", "", 10000, 8500, 35420, "-", 53920),
    ("1. 당기순이익", "", "-", "-", 13260, "-", 13260),
    ("2. 순확정급여부채의 재측정요소", "12", "-", "-", -250, "-", -250),
    ("3. 연차배당", "14", "-", "-", -2500, "-", -2500),
    ("2025.12.31(당기말)", "", 10000, 8500, 45930, "-", 64430),
]

# 주석 1~25: (제목, [문단], [(헤더행, [데이터행...]), ...])
NOTES = {
    1: ("일반사항", [
        "주식회사 한빛정밀(이하 \"회사\")은 2014년 3월 자동차용 정밀부품의 제조 및 "
        "판매를 목적으로 설립되었으며, 경기도 화성시에 본사 및 공장을 두고 있습니다. "
        "회사는 전동화 구동모듈용 정밀부품을 주력 제품으로 생산하고 있습니다.",
        "보고기간종료일 현재 발행주식총수는 보통주 2,000,000주(1주당 액면금액 "
        "5,000원)이며, 주요 주주는 ㈜한빛홀딩스 62.5% 및 기타 37.5%입니다. "
        "당기말 현재 종업원 수는 285명입니다."], []),
    2: ("재무제표 작성기준", [
        "회사의 재무제표는 한국채택국제회계기준(K-IFRS)에 따라 작성되었으며, "
        "계속기업 가정 하에 작성되었습니다.",
        "재무제표는 확정급여채무의 보험수리적 평가 등을 제외하고는 역사적원가를 "
        "측정기준으로 하며, 기능통화이자 표시통화는 대한민국 원화입니다."], []),
    3: ("중요한 회계정책", [
        "수익은 기업회계기준서 제1115호에 따라 재화의 통제가 고객에게 이전되는 "
        "시점에 인식합니다. 재고자산은 총평균법에 의한 저가법으로 측정합니다.",
        "유형자산은 정액법(건물 20~40년, 기계장치 8년, 차량운반구 5년)으로 "
        "감가상각하며, 개발비는 5년간 상각합니다. 리스는 기업회계기준서 제1116호에 "
        "따라 사용권자산과 리스부채를 인식하고, 금융상품은 제1109호에 따라 "
        "분류·측정합니다. 종업원급여와 관련하여 확정급여제도를 운영합니다."], []),
    4: ("중요한 회계추정 및 가정", [
        "주요 추정 대상은 매출채권의 기대신용손실, 재고자산의 순실현가능가치, "
        "확정급여채무의 보험수리적가정 및 이연법인세자산의 실현가능성입니다."], []),
    5: ("현금및현금성자산", [
        "보고기간종료일 현재 현금및현금성자산의 구성내역은 다음과 같습니다."], [
        (["구  분", "당기말", "전기말"], [
            ["보통예금", 9830, 8120],
            ["정기예금(3개월 이내)", 5400, 4360],
            ["합  계", 15230, 12480]])]),
    6: ("매출채권", [
        "보고기간종료일 현재 매출채권의 내역은 다음과 같으며, 당기 중 손실충당금은 "
        "기초 620백만원에서 설정 85백만원, 제각 (35)백만원을 반영하여 기말 "
        "670백만원입니다."], [
        (["구  분", "당기말", "전기말"], [
            ["매출채권", 29120, 25740],
            ["차감: 손실충당금", -670, -620],
            ["장부금액", 28450, 25120]])]),
    7: ("재고자산", [
        "보고기간종료일 현재 재고자산의 내역은 다음과 같습니다. 당기 중 매출원가로 "
        "인식한 재고자산평가손실은 120백만원(전기: 95백만원)입니다."], [
        (["구  분", "당기말", "전기말"], [
            ["제품", 6540, 5890],
            ["재공품", 4230, 3760],
            ["원재료", 8650, 7590],
            ["미착품", 450, 410],
            ["합  계", 19870, 17650]])]),
    8: ("유형자산", [
        "당기 중 유형자산의 증감내역은 다음과 같습니다. 보고기간종료일 현재 장부금액 "
        "29,020백만원의 토지 및 건물이 차입금 담보로 제공되어 있습니다"
        "(주석 11, 22 참조)."], [
        (["구  분", "토지", "건물", "기계장치", "차량운반구", "건설중인자산", "합계"], [
            ["기초 장부금액", 12500, 15840, 17230, 890, 2300, 48760],
            ["취득", "-", "-", 3420, 280, 6120, 9820],
            ["처분", "-", "-", -310, -20, "-", -330],
            ["감가상각", "-", -1120, -4760, -360, "-", -6240],
            ["대체", "-", 1800, 2530, "-", -4330, "-"],
            ["기말 장부금액", 12500, 16520, 18110, 790, 4090, 52010]]),
        (["구  분", "취득원가", "감가상각누계액", "장부금액"], [
            ["토지", 12500, "-", 12500],
            ["건물", 22400, -5880, 16520],
            ["기계장치", 44530, -26420, 18110],
            ["차량운반구", 2930, -2140, 790],
            ["건설중인자산", 4090, "-", 4090],
            ["합  계", 86450, -34440, 52010]])]),
    9: ("무형자산", [
        "보고기간종료일 현재 무형자산은 개발비 2,890백만원, 소프트웨어 980백만원, "
        "회원권 250백만원으로 합계 4,120백만원(전기말: 3,980백만원)입니다. 당기 "
        "무형자산상각비는 480백만원입니다."], []),
    10: ("리스", [
        "보고기간종료일 현재 사용권자산(건물)의 장부금액은 3,280백만원으로 유형자산에 "
        "포함되어 있으며, 리스부채는 유동 920백만원, 비유동 3,450백만원입니다. 당기 중 "
        "사용권자산 감가상각비 840백만원, 리스부채 이자비용 145백만원 및 단기리스 "
        "관련 비용 65백만원을 인식하였습니다."], []),
    11: ("차입금", [
        "보고기간종료일 현재 차입금의 내역은 다음과 같습니다."], [
        (["구  분", "차입처", "연이자율\n(%)", "만기", "당기말", "전기말"], [
            ["운영자금", "KB은행", "4.35", "2026-06", 7000, 6500],
            ["무역금융", "신한은행", "4.82", "2026-03", 5000, 4000],
            ["시설자금", "산업은행", "3.95", "2028-09", 15000, 18000],
            ["합  계", "", "", "", 27000, 28500]])]),
    12: ("순확정급여부채", [
        "보고기간종료일 현재 확정급여채무의 현재가치는 18,340백만원, 사외적립자산의 "
        "공정가치는 11,560백만원으로 순확정급여부채는 6,780백만원입니다. 주요 "
        "보험수리적가정은 할인율 3.8%(전기: 4.1%), 임금상승률 4.2%입니다."], [
        (["구  분", "금  액"], [
            ["기초 확정급여채무", 17060],
            ["당기근무원가", 1240],
            ["이자원가", 610],
            ["재측정요소", 320],
            ["급여지급액", -890],
            ["기말 확정급여채무", 18340]])]),
    13: ("자본금과 주식발행초과금", [
        "보고기간종료일 현재 수권주식수는 8,000,000주, 발행주식수는 보통주 "
        "2,000,000주(1주당 액면금액 5,000원)입니다. 자본금 10,000백만원과 "
        "주식발행초과금 8,500백만원은 설립 이후 변동이 없습니다."], []),
    14: ("이익잉여금", [
        "보고기간종료일 현재 이익잉여금은 이익준비금 1,250백만원과 미처분이익잉여금 "
        "44,680백만원으로 구성됩니다. 당기 중 지급한 배당금은 1주당 1,250원, 총 "
        "2,500백만원(배당성향 18.9%)입니다."], []),
    15: ("수익", [
        "당기 수익의 분해내역은 다음과 같습니다. 주요 고객 수익 비중은 A사 38%, "
        "B사 22%로 상위 2개사가 60%를 차지합니다."], [
        (["구  분", "당  기"], [
            ["제품매출(국내)", 94230],
            ["제품매출(수출)", 61350],
            ["임가공수익", 2840],
            ["합  계", 158420]])]),
    16: ("비용의 성격별 분류", [
        "당기 매출원가와 판매비와관리비의 성격별 분류는 다음과 같습니다."], [
        (["구  분", "당  기"], [
            ["원재료 사용액", 78340],
            ["종업원급여", 24560],
            ["감가상각비와 상각비", 6720],
            ["외주가공비", 12450],
            ["기타", 19030],
            ["합  계", 141100]])]),
    17: ("기타수익과 기타비용", [
        "당기 기타수익은 정부보조금 620백만원, 유형자산처분이익 10백만원, 잡이익 "
        "610백만원(합계 1,240백만원)이며, 기타비용은 기부금 180백만원, 잡손실 "
        "380백만원(합계 560백만원)입니다."], []),
    18: ("금융수익과 금융비용", [
        "당기 금융수익은 이자수익 890백만원이며, 금융비용은 이자비용 1,450백만원"
        "(차입금 1,305백만원, 리스부채 145백만원)입니다."], []),
    19: ("법인세", [
        "당기 법인세비용은 당기법인세 3,900백만원과 이연법인세 280백만원의 합계 "
        "4,180백만원이며, 유효세율은 24.0%입니다."], [
        (["구  분", "당  기"], [
            ["법인세비용차감전순이익", 17440],
            ["적용세율에 따른 법인세", 3840],
            ["비공제비용 등 조정", 340],
            ["법인세비용", 4180]])]),
    20: ("주당이익", [
        "기본주당이익은 당기순이익 13,260백만원을 가중평균유통보통주식수 "
        "2,000,000주로 나눈 6,630원(전기: 4,970원)이며, 희석효과는 없습니다."], []),
    21: ("특수관계자 거래", [
        "당기 중 특수관계자 거래내역은 다음과 같으며, 주요 경영진 보상은 단기급여 "
        "1,650백만원과 퇴직급여 170백만원의 합계 1,820백만원입니다."], [
        (["구  분", "매출", "매입", "채권", "채무"], [
            ["㈜한빛홀딩스(지배기업)", 8420, 1230, 1850, 340]])]),
    22: ("우발부채와 약정사항", [
        "보고기간종료일 현재 금융기관이 회사에 제공한 지급보증은 수입신용장 관련 "
        "2,400백만원이며, 차입 약정한도 35,000백만원 중 27,000백만원이 "
        "실행되었습니다. 계류 중인 소송사건은 없습니다."], []),
    23: ("금융상품", [
        "보고기간종료일 현재 범주별 금융자산의 내역은 다음과 같습니다. 금융부채는 "
        "매입채무 18,340백만원, 차입금 27,000백만원, 리스부채 4,370백만원으로 전부 "
        "상각후원가로 측정하며, 공정가치는 장부금액과 유의적 차이가 없습니다."], [
        (["구  분", "상각후원가\n측정 금융자산", "당기손익-공정가치", "합  계"], [
            ["현금및현금성자산", 15230, "-", 15230],
            ["매출채권", 28450, "-", 28450],
            ["금융자산 합계", 43680, "-", 43680]])]),
    24: ("위험관리", [
        "신용위험: 신규 거래처 신용평가를 실시하며 연체 3개월 초과 채권 비율은 "
        "0.8%입니다. 시장위험: 수출채권 USD 8.2백만달러의 환노출이 있으며 환율 10% "
        "변동 시 세전이익에 ±1,090백만원의 영향이 있습니다."], [
        (["구  분", "금  액"], [
            ["1년 이내", 38620],
            ["1년 초과 5년 이내", 26450]])]),
    25: ("보고기간 후 사건", [
        "2026년 2월 이사회에서 1주당 1,250원, 총 2,500백만원의 현금배당을 "
        "결의하였습니다. 동 배당금은 당기 재무제표에 부채로 인식되지 않았습니다."], []),
}


# ---------------------------------------------------------------------------
# 편집 로직
# ---------------------------------------------------------------------------

def _sheet_rowmap(wb):
    m = collections.defaultdict(dict)
    for row in wb["_MAP"].iter_rows(min_row=2, values_only=True):
        m[str(row[0])].setdefault(int(row[1]), []).append(int(row[2]))
    for sheet in m:
        for r in m[sheet]:
            m[sheet][r].sort()
    return m


def _edit_cover(ws, rowmap):
    """표지 템플릿의 placeholder(제 XX 기 / XXXX년) 채우기."""
    period_vals = iter(["제 12 기", "2025년 01월 01일", "2025년 12월 31일",
                        "제 11 기", "2024년 01월 01일", "2024년 12월 31일"])
    prev_label = None
    for r in sorted(rowmap):
        v = ws.cell(r, 1).value
        if v == "제 XX 기" or v == "XXXX년 XX월 XX일":
            try:
                ws.cell(r, 1).value = next(period_vals)
            except StopIteration:
                pass
        elif v is None and prev_label == "감사대상회사의 명칭":
            ws.cell(r, 1).value = COMPANY
        elif v is None and prev_label == "감사인 명칭":
            ws.cell(r, 1).value = "OO회계법인"
        if isinstance(v, str) and v.strip():
            prev_label = v.strip()


def _fix_title_cells(ws, rowmap, header_row):
    """제목 블록(2~5행)과 헤더행의 기수/회사명 교체."""
    for r in sorted(rowmap):
        if r > header_row:
            break
        for c in rowmap[r]:
            v = ws.cell(r, c).value
            if isinstance(v, str):
                nv = (v.replace("제 57", "제 12").replace("제 56", "제 11")
                      .replace("삼성전자주식회사", COMPANY))
                if nv != v:
                    ws.cell(r, c).value = nv


def _edit_fs(ws, rowmap, data_rows, report):
    """FS 시트: 헤더행 아래 데이터 행에 한빛 데이터를 순서대로, 나머지는 공란."""
    header_row = next(r for r in sorted(rowmap) if len(rowmap[r]) >= 4)
    _fix_title_cells(ws, rowmap, header_row)
    targets = [r for r in sorted(rowmap)
               if r > header_row and len(rowmap[r]) >= 3]
    for i, r in enumerate(targets):
        cols = rowmap[r]
        if i >= len(data_rows):
            for c in cols:
                ws.cell(r, c).value = None
            continue
        label, note, cur, pre, kind = data_rows[i]
        ws.cell(r, cols[0]).value = label
        if 2 in cols:
            ws.cell(r, 2).value = note or None
        amount_cols = [c for c in cols if c >= 3]
        if len(amount_cols) >= 4:
            pairs = [(amount_cols[0], amount_cols[1]),
                     (amount_cols[2], amount_cols[3])]
        elif len(amount_cols) == 2:
            # 기간별 단일 열 (colspan 병합 행): 계층 구분 없이 기입
            pairs = [(amount_cols[0], None), (amount_cols[1], None)]
        elif len(amount_cols) == 1:
            pairs = [(amount_cols[0], None), (None, None)]
        else:
            pairs = [(None, None), (None, None)]
        for v, (left, right) in zip((cur, pre), pairs):
            tgt = left if (right is None or kind == "item") else right
            for c in (left, right):
                if c:
                    ws.cell(r, c).value = \
                        _val(v) if (c == tgt and v is not None) else None
    if len(data_rows) > len(targets):
        report["fs_rows_dropped"] += len(data_rows) - len(targets)


def _edit_ce(ws, rowmap, report):
    """CE: 뼈대 7열(과목/주석/자본금/주발초/이잉/기타자본/총계)에 직접 매핑.

    헤더행의 "주식발행\\n초과금" 두 줄 라벨은 그대로 보존 (V6).
    """
    header_row = next(r for r in sorted(rowmap) if len(rowmap[r]) >= 5)
    _fix_title_cells(ws, rowmap, header_row)
    targets = [r for r in sorted(rowmap)
               if r > header_row and len(rowmap[r]) >= 3]
    for i, r in enumerate(targets):
        cols = rowmap[r]
        if i >= len(CE_ROWS):
            for c in cols:
                ws.cell(r, c).value = None
            continue
        vals = CE_ROWS[i]
        for j, c in enumerate(cols):
            ws.cell(r, c).value = _val(vals[j]) if j < len(vals) else None
    if len(CE_ROWS) > len(targets):
        report["fs_rows_dropped"] += len(CE_ROWS) - len(targets)


def _regions(rowmap):
    """다중 열 행들을 연속 블록(테이블 영역)으로 묶는다."""
    rows = [r for r in sorted(rowmap) if rowmap[r] != [1]]
    regions, cur = [], []
    for r in rows:
        if cur and r - cur[-1] > 1:
            regions.append(cur)
            cur = []
        cur.append(r)
    if cur:
        regions.append(cur)
    return regions


def _write_table(ws, rowmap, region, table, report):
    headers, data = table
    rows_needed = [headers] + data
    if len(rows_needed) > len(region):
        # 절단이 필요하면 꼬리(합계 행)를 보존: 헤더 + 마지막 행들 유지
        keep = len(region) - 1
        dropped = data[:len(data) - keep]
        rows_needed = [headers] + data[len(data) - keep:] if keep > 0 \
            else [headers]
        report["cells_dropped"] += sum(len(v) for v in dropped)
    for i, r in enumerate(region):
        cols = rowmap[r]
        if i >= len(rows_needed):
            for c in cols:
                ws.cell(r, c).value = None
            continue
        vals = rows_needed[i]
        for j, c in enumerate(cols):
            ws.cell(r, c).value = _val(vals[j]) if j < len(vals) else None
        if len(vals) > len(cols):
            report["cells_dropped"] += len(vals) - len(cols)


def _edit_note(ws, rowmap, n, report):
    ws.cell(1, 1).value = (f"{n}. {n}. {NOTES[n][0]}" if n in NOTES
                           else f"{n}. {n}. (여백)")
    slots = [r for r in sorted(rowmap) if r > 1 and rowmap[r] == [1]]
    regions = _regions(rowmap)

    paras = list(NOTES[n][1]) if n in NOTES else []
    tables = list(NOTES[n][2]) if n in NOTES else []

    # 문단 슬롯: 단위 표기는 보존, 나머지에 한빛 문안 채우고 남으면 공란
    # (첫 문단은 헤더 P의 SPAN 뒤 본문 구간 → 제목과 분리되도록 빈 줄 선행)
    if paras:
        paras = ["\n\n" + paras[0]] + paras[1:]
    text_slots = [r for r in slots
                  if not (isinstance(ws.cell(r, 1).value, str)
                          and ws.cell(r, 1).value.strip().startswith("(단위"))]
    for i, r in enumerate(text_slots):
        ws.cell(r, 1).value = paras[i] if i < len(paras) else None
    if paras and not text_slots:
        report["paras_dropped"] += len(paras)
    elif len(paras) > len(text_slots) and text_slots:
        # 남는 문단은 마지막 슬롯에 합침
        joined = "\n".join(paras[len(text_slots) - 1:])
        ws.cell(text_slots[-1], 1).value = joined

    # 테이블: 커버리지(행×열) 최대인 미사용 영역을 골라 기입, 나머지는 공란
    used = set()
    for table in tables:
        nrows = len(table[1]) + 1
        ncols = len(table[0])
        pick, best = None, -1
        for idx, region in enumerate(regions):
            if idx in used:
                continue
            rcols = max(len(rowmap[r]) for r in region)
            score = min(len(region), nrows) * min(rcols, ncols)
            if score > best:
                pick, best = idx, score
        if pick is None:
            report["tables_dropped"] += 1
            continue
        used.add(pick)
        _write_table(ws, rowmap, regions[pick], table, report)
    for idx, region in enumerate(regions):
        if idx in used:
            continue
        for r in region:
            for c in rowmap[r]:
                ws.cell(r, c).value = None


# 구조화 편집 후 전 시트에 적용하는 잔존 텍스트 치환 (표지 부속 테이블 등)
REPLACEMENTS = [
    ("삼성전자주식회사 대표이사 전영현", f"{COMPANY} 대표이사 김한빛"),
    ("삼성전자주식회사", COMPANY),
    ("삼성전자", "한빛정밀"),
    ("경기도 수원시 영통구 삼성로 129 (매탄동)", "경기도 화성시 동탄산단1길 12"),
    ("031-200-1114", "031-000-0000"),
    ("제 57", "제 12"),
    ("제 56", "제 11"),
    ("전영현", "김한빛"),
]


def _global_replace(wb, rowmaps):
    for sheet, rowmap in rowmaps.items():
        ws = wb[sheet]
        for r, cols in rowmap.items():
            for c in cols:
                v = ws.cell(r, c).value
                if not isinstance(v, str):
                    continue
                nv = v
                for old, new in REPLACEMENTS:
                    nv = nv.replace(old, new)
                if nv != v:
                    ws.cell(r, c).value = nv


# ---------------------------------------------------------------------------
# 빌드
# ---------------------------------------------------------------------------

def build(work_dir: str = None):
    """(오염본 경로, 클린본 경로, 리포트) 반환."""
    if not os.path.exists(SKELETON):
        raise FileNotFoundError(f"뼈대 DSD 없음: {SKELETON}")
    os.makedirs(SYN_DIR, exist_ok=True)
    work = work_dir or tempfile.mkdtemp(prefix="hanbit_")
    report = collections.Counter()

    xlsx = os.path.join(work, "skeleton.xlsx")
    extract(SKELETON, xlsx, keep_note_numbers=True)
    wb = load_workbook(xlsx)
    rowmaps = _sheet_rowmap(wb)

    _edit_cover(wb["표지"], rowmaps["표지"])
    _edit_fs(wb["BS"], rowmaps["BS"], BS_ROWS, report)
    _edit_fs(wb["PL"], rowmaps["PL"], PL_ROWS, report)
    _edit_fs(wb["PL1"], rowmaps["PL1"], PL1_ROWS, report)
    _edit_ce(wb["CE"], rowmaps["CE"], report)
    _edit_fs(wb["CF"], rowmaps["CF"], CF_ROWS, report)
    for n in range(1, 33):
        _edit_note(wb[str(n)], rowmaps[str(n)], n, report)
    _global_replace(wb, rowmaps)
    wb.save(xlsx)

    # 오염본: 뼈대의 "N. N." 헤더 + &cr;-only 319개 그대로 보존
    dirty = os.path.join(SYN_DIR, "한빛정밀_오염.dsd")
    res1 = repack(xlsx, SKELETON, dirty, clean_cr=False)
    report["edited_cells"] = len(res1["changes"])

    # 클린본: 오염본을 기본 파이프라인(정리 기능)으로 통과
    xlsx2 = os.path.join(work, "dirty_re.xlsx")
    extract(dirty, xlsx2)                       # 기본: 주석 번호 정리 표시
    clean = os.path.join(SYN_DIR, "한빛정밀_클린.dsd")
    res2 = repack(xlsx2, dirty, clean)          # 기본: &cr; 정리 포함
    report["clean_stage_changes"] = len(res2["changes"])

    # 잔존 뼈대 텍스트 (읽기전용 마크업 문단 한계) 집계
    from ..zipsplice import read_contents
    report["residual_samsung"] = read_contents(
        open(clean, "rb").read()).decode("utf-8").count("삼성")

    return dirty, clean, dict(report)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dirty, clean, rep = build()
    print("오염본:", dirty, f"({os.path.getsize(dirty):,} bytes)")
    print("클린본:", clean, f"({os.path.getsize(clean):,} bytes)")
    print("리포트:", rep)
