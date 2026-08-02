# [패치 V-2] XBRL 제출파일 속성 검증 — 기간·단위·주석 명칭

> 발원: 통합 지시 2026-08-02 STEP 3 (실검토 건 대응).
> 조립 원칙: 신규 파서 금지 — 기존 파서의 속성 판독 확장만.
> 경계: 판정 로직 `dsd_tool.attr_check`(dart_explorer 모름), 파싱·자산
> 준비는 조립층. LLM·송신 없음.

## 속성 원천 (전부 기존 자산·파서 확장)

| 대상 | 원천 | 확장 내용 |
|---|---|---|
| 표준 element 속성(type·balance·periodType) | 금감원 배포 엑셀 Concepts | D-2c 리졸버가 같은 행에서 속성 열 추가 로드 (`LabelResolver.attrs`) |
| 확장 element 속성 | 패키지 xsd | `TaxonomyPackage` 기존 xs:element 순회에서 속성 판독 (`ext_attrs`) |
| 단위(unitRef·measure) | 인스턴스 .xbrl | `XbrlInstance` 기존 순회에 unit 정의·팩트 unitRef 추가 (`units`, fact.unit) |
| 주석 role 한글·영문명 | 패키지 xsd roleType definition | 기존 `role_defs` — `한글 \| 영문` 파이프 병기 실측, 분리 사용 |

## 판정 3종

1. **① 기간 속성** — element periodType(표준=배포 엑셀 → 확장=xsd)
   ↔ 사용 contextRef 유형(instant/duration). 불일치=속성 위반(FALSE),
   원천 부재=판정 불가(정직 노출). **비교 쌍 존재 검사**: 당기
   (end=보고기간말) / 전기(end<보고기간말) 한쪽만 있으면 "당기만/
   전기만 사용" 목록화 — 판정 아닌 노출 (V-1 컨텍스트 선별·F-3b 기간
   체계 재사용).
2. **② 단위 속성** — element 유형(화폐/주당/주식수/비수치/순수) ↔
   unit measure(iso4217:KRW / shares / pure / 없음) 정합 + decimals
   관례({0, -3, -6, -8, -9, INF}) 검사, 문서 대표 decimals(최빈값)
   대비 상이 비고. V-1 단위 정규화 관례 재사용.
3. **③ 주석 명칭 대사** — DSD 주석 제목 ↔ 인스턴스 대표 주석
   role(D8…, 서브롤 제외) 한글 정의. 전기대사 제목 정규화 재사용.
   영문명은 role 정의의 파이프 뒤 영문 사용, 부재 시 role 코드
   대체+그 사실 명기. 역방향(제출파일에만 있는 role)도 노출.

## 산출 (A-5 규격)

요약(3종 판정 분포·쌍 한쪽만·role만·관례 decimals) + 시트
①기간속성 ②단위속성 ③주석명칭 — TRUE/FALSE+비고, FALSE 빨강,
판정 불가 노랑. Mapping 양식 미보유 확정 — 표준 리포트로 산출
(코멘트 수동 전기), 양식 도착 시 후속 소품.

## 게이트

- G1 3사 왕복(신원·무벡스·삼성 B-4 첨부) — 실측치는 게이트 보고 참조.
  **실공시에서 기간 속성 위반 4건씩 공통 검출** (특수관계자
  자금거래·현물출자 계열 duration 정의에 instant 사용 — 3사 공통
  패턴이라 '26 배포 엑셀과 '25 태깅 관행의 periodType 개정 차이
  가능성 병기, 회계사 확인 영역으로 노출)
- G2 변조 3종(periodType·decimals·주석명 각 1건) — 기준선 대비 신규
  전환이 변조분만인지 검사
- G3 전 테스트 회귀
