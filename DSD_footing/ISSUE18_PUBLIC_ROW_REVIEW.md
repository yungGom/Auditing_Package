## 한눈에 보기

### 1. 이번에 무엇을 했나?
공개 자료 네 건에서 끊긴 자동 연결을 원문과 행별로 대조했습니다. 연결이 유지된 항목의 후보 변동과 산술검사 변동도 별도로 확인했습니다.
### 2. 실제로 무엇이 달라졌나?
빠진 자동 연결 중82건은 프로그램을 더 보완할 문제로 분리했습니다. 서로 다른 측정값을 연결하던2건은 자동연결 제외가 타당합니다. 나머지3건은 금융자산 손익의 구성 근거가 부족해 검토 대상으로 유지합니다. 이번에는 제품을 변경하지 않았습니다.
### 3. 확인 결과는 어땠나?
기존 연결 감소와 검사 집계를 재현하고 모든 변경 항목에 분류 근거를 남겼습니다. 이전 공개 자료 비교 실패는 해소되지 않았습니다. 새로운 수정 필요 항목도 확인됐으므로 전체 통과나 업무 수용을 권고하지 않습니다.
### 4. 아직 남은 문제는?
주석 합계·표제·행 계층, 재무현금흐름 열, 연속표, 기간 출처를 더 정확히 읽어야 합니다. 실제 주주 비율 합계도 공백 표제 때문에 여전히 미검증입니다.
### 5. 내가 결정해야 할 게 있나?
지금 추가 승인은 필요 없습니다. 이미 요청한 대로 의미가 다른 비교는 검토 대상으로 유지합니다. 회계 검토 대상으로 남길 근거 부족 항목은 기타포괄손익과 금융자산 평가·처분손익의 남은 세 기간입니다. 퇴직급여 누적과 당반기 누적 금융자산 손익은 인접 원문에서 구성 근거를 확보했지만 기존 결정에 따른 검토 상태를 유지합니다. 같은 구성 전체임을 입증하기 전에는 자동 연결하지 않습니다. 나머지는 프로그램 보완 사항이며 사용자에게 항목별 수작업 검사를 요구하지 않습니다.
### 6. 지금 상태는?
사람 확인 필요. 원문 검토와 분류를 마치고 Owner Review에서 멈춥니다. 병합·배포·기준 변경·Issue 종결은 하지 않습니다.

## Developer Details

Report type: public-source per-row investigation / Owner Review, 2026-10-06. Issue #18 and related #27–#30, draft PR #31. Frozen comparison: main6373a333414f51015f9d1068e32ec2ef7702cbe4 vs implementation76a88c90b563ac8ea6bdc8bda20c62c852a476b4. This is source-supported review, not accounting assurance or a new implementation pass.

### Scope, identity and method

All4 registered public sample PDFs, original signs and declared units. Each PDF SHA256 and complete changed tables, headers, above-table words/geometry, page text, old/new record periods and roles are preserved in local `row-review-20261006/results.json`. Source PDF hashes match prior public investigation. The diagnostic executes an in-memory prefix of each version's actual final.py through its whole arithmetic/render-overlay loop and captures records immediately after verdict; it stops before PDF/workbook publication. The only capture insertion appends a record; no product source is edited. Cache supplies identical actual extracted text/words/table bboxes/cell grids/page dimensions and searches with the actual unchanged UNIT pattern. This fixes the earlier arithmetic replay's no-table-page carry limitation. Counts below agree with the previous official final run, but this is not a substitute for the official gate and does not prove all unmodified links.

This audit targets all changed main→primary-note candidate relations; it does not certify every unchanged or secondary cross-note tag, actual client compatibility or final rendered tickmarks. Relevant source layouts/footnotes were visually inspected on18 PDF pages; it is source-PDF review, not product GUI/render UAT.

### Lost main-link classification

Definitions: ‘적절한 제외’ means exclusion from automatic normal same-period linkage, not erasing the review record or finding a misstatement. ‘추가 수정 필요’ means explicit source information was missed; it does not authorize a looser numeric-only matcher. ‘근거 부족’ means the exact accounting composition bridge is not established. All remain candidates only.

|Sample|Lost main records|Appropriate exclusion|Further correction|Insufficient evidence|
|---|---:|---:|---:|---:|
|Samsung|21|2|19|0|
|Humax|15|0|15|0|
|LGES|39|0|36|3|
|Chosun|12|0|12|0|
|Total|87|2|82|3|

The87 records are current/prior/span-specific main amount cells, not87 distinct financial accounts or errors. These account for C linked235→148, unmatched149→236. No newly added main links.

### Remaining accounting question and source-supported review candidates

**One remaining insufficient-evidence relation, three period cells:** LGES p8/t1/r7/c3,c7,c9 → p29/t1/r11/c2,c4,c5: non-reclassified FVOCI OCI −7,533/213/1,650百만원 vs category ‘평가손익/처분손익’. Same signs, periods, amounts and reference5 support candidates, but the entire note row is not explicitly bridged to the same OCI component for these three periods. Keep unverified. Additional current-half cumulative evidence must not be extended to quarter or prior-half periods. A future bridge needs exact-period OCI composition, not a waiver of matching rules.

**Two relations now have stronger source evidence and move to further correction, while existing review status stays:**

1. LGES p8/t1/r6/c5 → p46/t1/r6/c2, OCIcum1,030: p44 explicitly defines netDB as obligation minus assets; p45's current-half obligation remeasurement fourrows are explicitly printed `-`; p46 current-half asset remeasurement return is1,030; p8 OCIcum is+1,030 with tax effect separately stated. That supports a composition/sign reconciliation rather than amount coincidence. Source `-` is explicit displayednil, not extractingNone or missinginput and fillingzero. Existing Owner review remains; no blanket net-liability-to-asset-return equivalence is approved.
2. LGES p8/t1/r7/c5 → p29/t1/r11/c3, FVOCIcurrentcum−10,154: p32 explicitly labels the current-half equity-instrument valuation change as ‘법인세효과 차감전, 기타포괄손익 항목’−10,154, with disposal−2,762 separately stated. p28 strategic-equity FVOCI designation supports the category. p32 prior column is annual818, not prior-half1,650, so it cannot establish the remaining periods. Preserve the review status and period-limited candidate evidence.

The initial80/2/5 draft classification was revised to82/2/3 after expanding source inspection to p28/p32/p44–46. This is correction based on additional source evidence, independently rechecked; it is not a change to product results or approval status. Supplementary exact source text/tables are saved with PDF identity in `supplemental-source.json`.

Samsung SCE purchase→prior treasury-stock closing balance2cells already have an Owner decision to remainreview. They are appropriately excluded from automatic assurance; no repeated approval question. Details and source coordinates below remain visible.

### Concrete correction work, not Owner accounting questions

- Income/expense totals: source tables and titled sections clearly associate ‘계/합계’ with SG&A, other/financial income/cost, sales/cost, operatingloss or cash-flow adjustments. `_role` ignores the source block's meaning; exact flow-label equality separately rejects known titled totals or supported aliases. Preserve numeric/period safeguards and establish identity from table title/row hierarchy, not blanket synonyming or equality-guard removal.
- Mixed balance/movement columns: Samsung p79 and LGES p66 have explicit 재무현금흐름 columns. They are flows despite borrowing/bond account row names. Conversely LGES p43 residual total after current-liability deduction is noncurrent closingprovision. Cell column and row context must both control role.
- Period leakage/continuation: Humax p121 prior contract liability has an explicit dual-side header and current/prior subsection; a preceding current-only narrative leaks into the next table. Chosun p40→41 current-intangible and p61→62 adjustment tables retain traceable source continuity; strict continuation leaves themunknown. Correct physical/source ownership without value-derived inheritance. Some retained-note coverage losses include Chosun p34→35 and Humax spaced 기 초/기 말 headers.
- Date anchors: LGES annualend and quarterly/cumulative range dates are unioned by financial-period number. Current3M/cumulative records share2025-1-1,2025-4-1,2025-6-30; prior includes2024-12-31 too. That set is not an exact duration identity. Bind dates per statement/table/column span; no Owner request to waive span identity.
- Balance-account words also need bounded identity: closing-balance rows such as 수익증권, 상각후원가측정금융자산 and 공정가치 금융부채 are not income/amortization flows merely because their names contain 수익/상각/손익. Header/row/block evidence must control the cell role.
- Humax p16 actual `주 요 주 주` header contains spaces.35.68+13.19+51.13=100 is the same shareholder distribution. Raw substring recognition leaves itSKIP. Header normalization is a correction; business scope was already reviewed.

### Arithmetic variations

22 changed record payloads:1 further-correction ratio OK→SKIP;2 valid small-interest additions OK;9 added excluded A1SKIP;8 pre-existing A2SKIP calculated-value changes;2 Chosun percentage OK records retain their verdict and only gain ratio metadata. Thus totalA+11, OK+1, SKIP+10 across allsamples; remaining verdict counts unchanged. Excluded time/headcount tables do not represent monetary assurance. All22 rows are separately listed; ‘valid addition/existing check retained’ are explanatory A categories, not hidden C three-way classification.

### Verification and boundaries

- `python -B ../row_review.py`: executed4/4 public samples, diagnosticexit0. Captured Acounts and Ccounts exactly match previous official final gate. Assertions/checks and hashes recorded below.
- Fresh official `python -B scripts/test_dsd_footing.py` (2026-10-06): **0/4 PASS,4/4 FAIL**, exit1, unchanged protectedGATES, no skip/update/waiver. All4 samples executed again, reproducing the same15 metric differences in `official-gates.log`, exit1 in `official-gates.exit`. No skips, baseline updates, product code or threshold changes. A failed comparison is not a release assertion.
- Protected check and report-diff check: final results recorded below. Focused30 tests previouslyPASS on unchanged implementation; not rerun for a documentation-only diagnostic pass.
- Fullrepo/shared regressions, final tickmark-render comparison, GUI/manual UAT, Linux/private realmaterial compatibility: NOT RUN. No all-tests-pass assertion.
- Independent reviewer checks the classification and audit coverage; reviewer results below.

### Complete lost main-record ledger

Coordinates below are1-based physical PDFpage/table/extractedrow/column (printed DARTpage usuallyone less). Stable IDs map to the local CSV and full sourceJSON. All87 records included; no default ‘accepted’ classification based on amount alone.

|ID|Sample|Main p/t/r/c|Label / displayedamount|Old primary note p/t/r/c|Classification|Source reason|
|---|---|---|---|---|---|---|
|C-S01|Samsung|12/1/5/3|판매비와관리비 / 48445100.0 (×1000000원)|70/1/16/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-S02|Samsung|12/1/5/5|판매비와관리비 / 44629735.0 (×1000000원)|70/1/16/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-S03|Samsung|12/1/7/3|기 타 수 익 / 9815254.0 (×1000000원)|71/1/7/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-S04|Samsung|12/1/7/5|기 타 수 익 / 10351185.0 (×1000000원)|71/1/7/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-S05|Samsung|12/1/8/3|기 타 비 용 / 247096.0 (×1000000원)|71/1/12/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-S06|Samsung|12/1/8/5|기 타 비 용 / 540542.0 (×1000000원)|71/1/12/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-S07|Samsung|12/1/9/3|금 융 수 익 / 7445403.0 (×1000000원)|72/1/7/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-S08|Samsung|12/1/9/5|금 융 수 익 / 7717689.0 (×1000000원)|72/1/7/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-S09|Samsung|12/1/10/3|금 융 비 용 / 7181098.0 (×1000000원)|72/1/14/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-S10|Samsung|12/1/10/5|금 융 비 용 / 8139788.0 (×1000000원)|72/1/14/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-S11|Samsung|12/1/12/3|법 인 세 비 용(수 익) / -250519.0 (×1000000원)|73/1/11/2; 73/2/11/2|추가 수정 필요|본표와 해당 주석의 세금/계속·중단영업 계산 표제 및 행 구성으로 대응함. 단순 라벨 문자열 불일치/역할 미해석으로 누락.|
|C-S12|Samsung|12/1/12/5|법 인 세 비 용(수 익) / -1832987.0 (×1000000원)|73/1/11/3; 73/2/11/3|추가 수정 필요|본표와 해당 주석의 세금/계속·중단영업 계산 표제 및 행 구성으로 대응함. 단순 라벨 문자열 불일치/역할 미해석으로 누락.|
|C-S13|Samsung|14/1/9/6|2. 자기주식의 취득 / -1811775.0 (×1000000원)|67/1/4/3|적절한 제외|자기주식 취득 거래액과 전기말 자기주식 잔액은 다른 측정값. 자동 정상연결 제외가 타당하며 검토 기록은 유지.|
|C-S14|Samsung|14/1/9/7|2. 자기주식의 취득 / -1811775.0 (×1000000원)|67/1/4/3|적절한 제외|자기주식 취득 거래액과 전기말 자기주식 잔액은 다른 측정값. 자동 정상연결 제외가 타당하며 검토 기록은 유지.|
|C-S15|Samsung|15/1/5/3|나. 조정 / 33652598.0 (×1000000원)|77/1/14/2|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-S16|Samsung|15/1/5/5|나. 조정 / 21493129.0 (×1000000원)|77/1/14/3|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-S17|Samsung|15/1/6/3|다. 영업활동으로 인한 자산부채의 변동 / -4707300.0 (×1000000원)|78/1/15/2|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-S18|Samsung|15/1/6/5|다. 영업활동으로 인한 자산부채의 변동 / -760086.0 (×1000000원)|78/1/15/3|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-S19|Samsung|15/1/23/3|1. 단기차입금의 순증가(감소) / 4498284.0 (×1000000원)|79/1/3/3|추가 수정 필요|원문 재무현금흐름 열의 단기차입금 순증감/상환을 잔액으로 오인. 기초·기말 열과 구분해야 함.|
|C-S20|Samsung|15/1/23/5|1. 단기차입금의 순증가(감소) / 5316919.0 (×1000000원)|79/2/3/3|추가 수정 필요|원문 재무현금흐름 열의 단기차입금 순증감/상환을 잔액으로 오인. 기초·기말 열과 구분해야 함.|
|C-S21|Samsung|15/1/25/5|3. 사채 및 장기차입금의 상환 / -217305.0 (×1000000원)|79/2/4/3|추가 수정 필요|원문 재무현금흐름 열의 단기차입금 순증감/상환을 잔액으로 오인. 기초·기말 열과 구분해야 함.|
|C-H01|Humax|8/1/32/5|계약부채 / 347666628.0 (×1원)|121/2/2/3|추가 수정 필요|원문 전기말(주3)과 (5) 당기말/전기말 표제 명시. 앞 (4) 당기말 문장이 새 표로 누출. 주2의 다른 항목은 선수수익에 포함되므로347,667천원 구성 대응 근거 있음.|
|C-H02|Humax|10/1/5/3|기타영업외수익 / 11068220283.0 (×1원)|123/1/11/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-H03|Humax|10/1/5/4|기타영업외수익 / 11334873751.0 (×1원)|123/1/11/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-H04|Humax|10/1/6/3|기타영업외비용 / 19488939780.0 (×1원)|123/2/11/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-H05|Humax|10/1/6/4|기타영업외비용 / 18064618223.0 (×1원)|123/2/11/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-H06|Humax|10/1/10/3|IV. 법인세비용차감전순손실 / -55889341432.0 (×1원)|128/1/3/2|추가 수정 필요|본표와 해당 주석의 세금/계속·중단영업 계산 표제 및 행 구성으로 대응함. 단순 라벨 문자열 불일치/역할 미해석으로 누락.|
|C-H07|Humax|10/1/10/4|IV. 법인세비용차감전순손실 / -46500215280.0 (×1원)|128/1/3/3|추가 수정 필요|본표와 해당 주석의 세금/계속·중단영업 계산 표제 및 행 구성으로 대응함. 단순 라벨 문자열 불일치/역할 미해석으로 누락.|
|C-H08|Humax|10/1/11/3|V. 법인세비용 / 2921557111.0 (×1원)|127/1/10/2; 128/1/18/2|추가 수정 필요|본표와 해당 주석의 세금/계속·중단영업 계산 표제 및 행 구성으로 대응함. 단순 라벨 문자열 불일치/역할 미해석으로 누락.|
|C-H09|Humax|10/1/11/4|V. 법인세비용 / 4051955223.0 (×1원)|127/1/10/3; 128/1/18/3|추가 수정 필요|본표와 해당 주석의 세금/계속·중단영업 계산 표제 및 행 구성으로 대응함. 단순 라벨 문자열 불일치/역할 미해석으로 누락.|
|C-H10|Humax|10/1/13/3|중단영업손실 / -3226338193.0 (×1원)|164/1/7/2|추가 수정 필요|본표와 해당 주석의 세금/계속·중단영업 계산 표제 및 행 구성으로 대응함. 단순 라벨 문자열 불일치/역할 미해석으로 누락.|
|C-H11|Humax|10/1/13/4|중단영업손실 / -29730744092.0 (×1원)|164/1/7/3|추가 수정 필요|본표와 해당 주석의 세금/계속·중단영업 계산 표제 및 행 구성으로 대응함. 단순 라벨 문자열 불일치/역할 미해석으로 누락.|
|C-H12|Humax|13/1/5/3|수익비용의 조정 / 91103872621.0 (×1원)|160/1/17/2|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-H13|Humax|13/1/5/5|수익비용의 조정 / 101109956217.0 (×1원)|160/1/17/3|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-H14|Humax|13/1/6/3|운전자본의 변동 / 72290036101.0 (×1원)|161/1/13/2|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-H15|Humax|13/1/6/5|운전자본의 변동 / 36454509823.0 (×1원)|161/1/13/3|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-L01|LGES|6/1/34/3|4. 비유동성충당부채 / 176334.0 (×1000000원)|43/3/8/5|추가 수정 필요|기말 충당부채에서 유동항목 차감 후 합계가 비유동성 충당부채. 거래액 합계가 아니라 잔액 합계로 문맥을 읽어야 함.|
|C-L02|LGES|6/1/34/5|4. 비유동성충당부채 / 147019.0 (×1000000원)|43/4/8/5|추가 수정 필요|기말 충당부채에서 유동항목 차감 후 합계가 비유동성 충당부채. 거래액 합계가 아니라 잔액 합계로 문맥을 읽어야 함.|
|C-L03|LGES|7/1/3/3|I. 매출 / 1744834.0 (×1000000원)|53/1/3/2; 53/2/5/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L04|LGES|7/1/3/4|I. 매출 / 3921902.0 (×1000000원)|53/1/3/3; 53/2/5/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L05|LGES|7/1/3/5|I. 매출 / 1654590.0 (×1000000원)|53/1/3/4; 53/2/5/4|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L06|LGES|7/1/3/6|I. 매출 / 3562521.0 (×1000000원)|53/1/3/5; 53/2/5/5|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L07|LGES|7/1/4/3|II. 매출원가 / 1409517.0 (×1000000원)|53/1/4/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L08|LGES|7/1/4/4|II. 매출원가 / 3145431.0 (×1000000원)|53/1/4/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L09|LGES|7/1/4/5|II. 매출원가 / 1498659.0 (×1000000원)|53/1/4/4|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L10|LGES|7/1/4/6|II. 매출원가 / 2936096.0 (×1000000원)|53/1/4/5|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L11|LGES|7/1/6/3|IV. 판매비와 관리비 / 548661.0 (×1000000원)|53/1/6/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L12|LGES|7/1/6/4|IV. 판매비와 관리비 / 1303849.0 (×1000000원)|53/1/6/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L13|LGES|7/1/6/5|IV. 판매비와 관리비 / 782307.0 (×1000000원)|53/1/6/4|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L14|LGES|7/1/6/6|IV. 판매비와 관리비 / 1524787.0 (×1000000원)|53/1/6/5|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L15|LGES|7/1/7/3|V. 영업손실 / -213344.0 (×1000000원)|53/1/23/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L16|LGES|7/1/7/4|V. 영업손실 / -527378.0 (×1000000원)|53/1/23/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L17|LGES|7/1/7/5|V. 영업손실 / -626376.0 (×1000000원)|53/1/23/4|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L18|LGES|7/1/7/6|V. 영업손실 / -898362.0 (×1000000원)|53/1/23/5|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L19|LGES|7/1/8/3|VI. 금융수익 / 621249.0 (×1000000원)|55/1/8/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L20|LGES|7/1/8/4|VI. 금융수익 / 787430.0 (×1000000원)|55/1/8/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L21|LGES|7/1/8/5|VI. 금융수익 / 177236.0 (×1000000원)|55/1/8/4|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L22|LGES|7/1/8/6|VI. 금융수익 / 371933.0 (×1000000원)|55/1/8/5|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L23|LGES|7/1/9/3|VII. 금융비용 / 845048.0 (×1000000원)|55/1/13/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L24|LGES|7/1/9/4|VII. 금융비용 / 1017403.0 (×1000000원)|55/1/13/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L25|LGES|7/1/9/5|VII. 금융비용 / 188869.0 (×1000000원)|55/1/13/4|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L26|LGES|7/1/9/6|VII. 금융비용 / 381580.0 (×1000000원)|55/1/13/5|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L27|LGES|7/1/11/3|IX. 기타영업외비용 / 228758.0 (×1000000원)|56/2/10/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L28|LGES|7/1/11/4|IX. 기타영업외비용 / 289814.0 (×1000000원)|56/2/10/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L29|LGES|7/1/11/5|IX. 기타영업외비용 / 68020.0 (×1000000원)|56/2/10/4|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L30|LGES|7/1/11/6|IX. 기타영업외비용 / 128452.0 (×1000000원)|56/2/10/5|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-L31|LGES|8/1/6/5|(1) 순확정급여부채의 재측정요소 / 1030.0 (×1000000원)|46/1/6/2|추가 수정 필요|p44 순확정급여채무−적립자산 구조, p45 당반기 채무 재측정4행 명시 -, p46 자산 재측정수익1,030, p8 세전OCI누적1,030으로 구성 연결 근거 확보. 이 기간 후보에 한정하며 기존 검토 상태 유지; 일반 자동연결 승인 아님.|
|C-L32|LGES|8/1/7/3|(2) 기타포괄손익-공정가치 금융자산 손익 / -7533.0 (×1000000원)|29/1/11/2|근거 부족|본표 재분류되지 않는 OCI와 주석 평가손익/처분손익의 해당 금융자산 행은 강한 후보이나, 전액이 같은 OCI 구성이라는 연결 근거가 없음. 당반기3개월/전반기3개월/전반기누적 세 기간 검토. 당반기누적 근거를 확장하지 않음.|
|C-L33|LGES|8/1/7/5|(2) 기타포괄손익-공정가치 금융자산 손익 / -10154.0 (×1000000원)|29/1/11/3|추가 수정 필요|p32 당반기 평가손익 −10,154를 법인세효과 차감전 기타포괄손익 항목이라고 명시하며 처분은 별도 표시. p8/p29 당반기누적 후보 연결 근거 확보. 기존 검토 상태 유지; 다른 기간으로 확장하지 않음.|
|C-L34|LGES|8/1/7/7|(2) 기타포괄손익-공정가치 금융자산 손익 / 213.0 (×1000000원)|29/1/11/4|근거 부족|본표 재분류되지 않는 OCI와 주석 평가손익/처분손익의 해당 금융자산 행은 강한 후보이나, 전액이 같은 OCI 구성이라는 연결 근거가 없음. 당반기3개월/전반기3개월/전반기누적 세 기간 검토. 당반기누적 근거를 확장하지 않음.|
|C-L35|LGES|8/1/7/9|(2) 기타포괄손익-공정가치 금융자산 손익 / 1650.0 (×1000000원)|29/1/11/5|근거 부족|본표 재분류되지 않는 OCI와 주석 평가손익/처분손익의 해당 금융자산 행은 강한 후보이나, 전액이 같은 OCI 구성이라는 연결 근거가 없음. 당반기3개월/전반기3개월/전반기누적 세 기간 검토. 당반기누적 근거를 확장하지 않음.|
|C-L36|LGES|10/1/3/3|1. 영업으로부터 창출된 현금흐름 / -442728.0 (×1000000원)|65/1/27/2|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-L37|LGES|10/1/3/5|1. 영업으로부터 창출된 현금흐름 / 666860.0 (×1000000원)|65/1/27/3|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-L38|LGES|10/1/27/5|(1) 차입금의 증가 / 1595376.0 (×1000000원)|66/2/5/3|추가 수정 필요|전반기 재무현금흐름 열의 사채 증가/단기차입금 상환. 기간·열 역할을 읽지 못해 정상 후보 누락.|
|C-L39|LGES|10/1/29/5|(1) 차입금의 상환 / -15704.0 (×1000000원)|66/2/3/3|추가 수정 필요|전반기 재무현금흐름 열의 사채 증가/단기차입금 상환. 기간·열 역할을 읽지 못해 정상 후보 누락.|
|C-C01|Chosun|8/1/13/3|무형자산 / 12271790.0 (×1000원)|41/1/4/6|추가 수정 필요|p40 당기 무형자산 시작표와 p41 이어지는 기말12,271,790. 원문 연속표 근거가 있으나 기간을 복원하지 못함.|
|C-C02|Chosun|10/1/5/3|판매비와관리비 / 44094502.0 (×1000원)|56/2/16/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-C03|Chosun|10/1/9/3|금융수익 / 7366541.0 (×1000원)|57/2/9/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-C04|Chosun|10/1/9/4|금융수익 / 5819568.0 (×1000원)|57/2/9/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-C05|Chosun|10/1/10/3|금융원가 / 35322761.0 (×1000원)|57/2/16/2|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-C06|Chosun|10/1/10/4|금융원가 / 12032818.0 (×1000원)|57/2/16/3|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-C07|Chosun|10/1/12/3|지분법손익 / 7975319.0 (×1000원)|43/1/9/6|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-C08|Chosun|10/1/12/4|지분법손익 / -11454205.0 (×1000원)|43/2/9/6|추가 수정 필요|매출·원가·판매관리비·금융/기타손익의 동기간 세부내역 또는 합계. 표제·행 계층으로 본표 항목과 대응하며 역할/라벨 해석 누락.|
|C-C09|Chosun|13/1/5/3|조정 / 36474976.0 (×1000원)|62/1/8/2|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-C10|Chosun|13/1/5/4|조정 / 34541180.0 (×1000원)|62/1/8/3|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-C11|Chosun|13/1/6/3|순운전자본의 변동 / -15286106.0 (×1000원)|62/2/12/2|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|
|C-C12|Chosun|13/1/6/4|순운전자본의 변동 / 24072981.0 (×1000원)|62/2/12/3|추가 수정 필요|현금흐름 조정/운전자본/영업현금 세부내역의 동기간 합계. 표제·계층 또는 연속표를 읽지 못함.|

### Retained main-link candidate ledger

These47 mainrecords remain linked, but their65 removed candidate pairs are included below:20 appropriate automatic exclusions and45 further-correction candidates. Across all134 changed mainrecords (87 lost+47 retained),160 candidate pairs were removed:22 appropriate exclusions,135 further-correction candidates,3 insufficient-evidence candidates. No new primary candidate pairs were added. Counts of mainrecords and pairs are different denominators. Different-period closing/opening exclusion follows the current same-period C scope; this does not declare a supported carry-forward economically invalid. A separate opening/closing bridge is not silently approved. Source-backed same-period duplicate candidate losses are further-correction coverage, not a new count of unmatched mains.

|Pair|Sample|Main|Note|Classification|Source reason|
|---|---|---|---|---|---|
|P001|Samsung|10/1/12/5|38/1/2/2|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P002|Samsung|10/1/13/5|43/1/2/2|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P003|Samsung|10/1/14/5|48/1/2/7|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P004|Samsung|10/1/15/5|50/1/2/5|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P005|Samsung|10/1/17/5|74/1/22/2|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P029|Humax|8/1/10/3|145/1/5/3|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P030|Humax|8/1/10/3|145/1/5/4|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P031|Humax|8/1/10/5|145/2/5/3|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P032|Humax|8/1/10/5|145/2/5/4|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P033|Humax|8/1/19/5|83/1/15/2|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P034|Humax|8/1/20/3|87/2/12/9|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P035|Humax|8/1/20/5|87/2/12/2|적절한 제외|현재/이전 기간이 다름. 같은 금액이어도 동기간 자동연결 후보에서 제외.|
|P036|Humax|8/1/21/5|90/1/4/2|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P037|Humax|8/1/22/5|91/2/5/2|적절한 제외|현재/이전 기간이 다름. 같은 금액이어도 동기간 자동연결 후보에서 제외.|
|P038|Humax|8/1/23/3|93/2/6/8|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P039|Humax|8/1/23/5|93/2/6/2|적절한 제외|현재/이전 기간이 다름. 같은 금액이어도 동기간 자동연결 후보에서 제외.|
|P041|Humax|8/1/35/5|96/2/6/7|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P042|Humax|10/1/2/3|69/1/7/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P043|Humax|10/1/2/3|120/1/15/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P044|Humax|10/1/2/4|69/1/7/3|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P045|Humax|10/1/2/4|120/1/15/3|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P046|Humax|10/1/3/3|122/1/13/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P047|Humax|10/1/3/4|122/1/13/3|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P052|Humax|10/1/7/3|124/2/12/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P053|Humax|10/1/7/4|124/2/12/3|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P054|Humax|10/1/8/3|125/2/12/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P055|Humax|10/1/8/4|125/2/12/3|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P068|LGES|6/1/17/5|35/1/2/2|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P069|LGES|6/1/18/5|37/1/2/2|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P070|LGES|6/1/31/3|23/1/23/4|적절한 제외|현재/이전 기간이 다름. 같은 금액이어도 동기간 자동연결 후보에서 제외.|
|P071|LGES|6/1/31/3|28/2/5/2|적절한 제외|현재/이전 기간이 다름. 같은 금액이어도 동기간 자동연결 후보에서 제외.|
|P072|LGES|6/1/31/3|28/2/5/4|적절한 제외|현재/이전 기간이 다름. 같은 금액이어도 동기간 자동연결 후보에서 제외.|
|P073|LGES|6/1/31/5|23/1/23/2|적절한 제외|현재/이전 기간이 다름. 같은 금액이어도 동기간 자동연결 후보에서 제외.|
|P074|LGES|6/1/31/5|27/2/5/2|적절한 제외|현재/이전 기간이 다름. 같은 금액이어도 동기간 자동연결 후보에서 제외.|
|P075|LGES|6/1/31/5|27/2/5/4|적절한 제외|현재/이전 기간이 다름. 같은 금액이어도 동기간 자동연결 후보에서 제외.|
|P076|LGES|6/1/33/3|32/1/8/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P120|Chosun|8/1/4/3|35/1/3/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P121|Chosun|8/1/4/4|35/1/3/4|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P122|Chosun|8/1/5/3|35/1/4/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P123|Chosun|8/1/5/4|35/1/4/4|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P124|Chosun|8/1/7/3|35/1/5/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P125|Chosun|8/1/7/3|35/1/5/3|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P126|Chosun|8/1/7/3|36/2/4/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P127|Chosun|8/1/7/3|37/3/3/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P128|Chosun|8/1/9/3|35/1/6/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P129|Chosun|8/1/9/4|35/1/6/4|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P131|Chosun|8/1/15/3|44/3/6/5|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P132|Chosun|8/1/15/3|44/3/6/8|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P133|Chosun|8/1/15/4|43/1/8/3|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P134|Chosun|8/1/16/3|35/1/7/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P135|Chosun|8/1/16/3|35/1/7/3|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P136|Chosun|8/1/16/4|35/1/7/4|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P137|Chosun|8/1/16/4|35/1/7/5|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P138|Chosun|8/1/16/4|36/1/3/3|적절한 제외|전기말 본표와 당기초 주석은 서로 다른 기준일. 현재 동기간 연결 규칙에서 제외하며, 별도 이월검사로 자동 승계하지 않음. 원문이 틀렸다는 판정은 아님.|
|P139|Chosun|8/1/16/4|36/1/7/5|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P140|Chosun|8/1/17/3|35/1/8/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P141|Chosun|8/1/17/3|35/1/8/3|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P142|Chosun|8/1/17/4|35/1/8/4|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P143|Chosun|8/1/17/4|35/1/8/5|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P144|Chosun|8/1/18/3|35/1/9/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P145|Chosun|8/1/18/4|35/1/9/4|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P146|Chosun|8/1/25/3|35/1/11/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P147|Chosun|8/1/25/4|35/1/11/4|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P148|Chosun|8/1/26/3|35/1/12/2|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|
|P149|Chosun|8/1/26/4|35/1/12/4|추가 수정 필요|같은 항목/기간을 설명하는 원문 표제·열 또는 연속표가 존재함. 주석 후보 일부의 기간/잔액·거래액/합계 역할을 읽지 못함. 다른 후보가 남아 본표 연결수에는 변화 없음.|

### Complete A variation ledger

|ID|Sample|Source|Check|Before|After|Classification|Reason|
|---|---|---|---|---|---|---|---|
|A01|Humax|16/1/5/3|A1|OK|SKIP|추가 수정 필요|주 요 주 주 표제의 공백 때문에 주주분포 합계100을 인식하지 못함. 독립 회사 지분율 문제가 아님.|
|A02|Humax|167/2/4/-|A2|SKIP|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A03|Humax|167/2/5/-|A2|SKIP|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A04|Humax|167/2/6/-|A2|SKIP|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A05|Humax|167/2/7/12|A1|없음|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A06|Humax|167/2/7/3|A1|없음|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A07|Humax|167/2/7/4|A1|없음|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A08|Humax|167/2/7/5|A1|없음|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A09|Humax|167/2/7/6|A1|없음|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A10|Humax|167/2/7/-|A2|SKIP|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A11|LGES|59/1/42/5|A1|없음|OK|타당한 검사 확대|특수관계자 이자비용의 작은 표시금액34/20백만원 합계. 금액 열을 주석번호로 오인하던 누락 보완.|
|A12|LGES|60/1/39/5|A1|없음|OK|타당한 검사 확대|특수관계자 이자비용의 작은 표시금액34/20백만원 합계. 금액 열을 주석번호로 오인하던 누락 보완.|
|A13|Chosun|51/2/5/3|A1|OK|OK|기존 검사 유지|조선내화 구성비99.9+0.1=100; 판정 유지, ratio 역할 메타데이터만 추가.|
|A14|Chosun|51/2/5/5|A1|OK|OK|기존 검사 유지|조선내화 구성비99.9+0.1=100; 판정 유지, ratio 역할 메타데이터만 추가.|
|A15|Chosun|75/2/4/-|A2|SKIP|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A16|Chosun|75/2/5/-|A2|SKIP|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A17|Chosun|75/2/6/-|A2|SKIP|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A18|Chosun|75/2/7/3|A1|없음|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A19|Chosun|75/2/7/4|A1|없음|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A20|Chosun|75/2/7/5|A1|없음|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A21|Chosun|75/2/7/6|A1|없음|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|
|A22|Chosun|75/2/7/-|A2|SKIP|SKIP|적절한 제외|감사 투입 인원·시간 표의 기존 제외 규칙 유지. 새 후보/계산값 변화가 있어도 SKIP이며 정상검사 또는 금융금액으로 확정하지 않음.|

### Evidence closure

Protected `python -B scripts/check_protected.py --base origin/main`: PASS (2026-10-06), no protected definition/file changed. `git diff --check`: PASS. Source-hash and A/C metric comparison against prior official evidence:4/4 match. Final CSV completeness/uniqueID/count checks:87/160/22 PASS. Fresh official gate0/4PASS,4/4FAIL/exit1 with15 unchanged deltas; no skips. Local `consistency.log`, `protected.log`, `official-gates.log` retain evidence. No overall Technical PASS.

Independent reviewer `/root/issues27_30_review` checked every CSV count/coordinate coverage and representative source-grounded mechanisms, then independently checked the added source bridge evidence. Final classification82/2/3 agreed; original80/2/5 draft corrected by additional source evidence. No blocking classification disagreement. This is not independent accounting certification of every87 amount cell or of unchanged links. Reviewed labels/amounts and record/pair denominator clarifications were corrected. Evidence: `independent-classification-review.txt`. Newly evidenced product gaps remain unresolved; a prior scoped code review with no blockers does not establish current product completion.

Tracked ledgers: [Lost main records](reviews/issue18-20261006/lost-main-ledger.csv), [All removed primary candidates](reviews/issue18-20261006/removed-candidate-ledger.csv), [Arithmetic changes](reviews/issue18-20261006/arithmetic-ledger.csv), [Supplementary public source](reviews/issue18-20261006/supplemental-source.json). These are analysis records, not protected truth sets or acceptance baseline replacements.

|Public PDF|SHA256|
|---|---|
|삼성전자_감사보고서.pdf|`b9207f0f02e251658f523d2e26f84d7bf6b2e5e0187e5cb95aa73e552c884203`|
|[휴맥스홀딩스]연결감사보고서(2025.03.19).pdf|`b27fc753cbc3bbe221a5b5cdfb1d82126fe8130804aed0379ea4c5f5aeace792`|
|[LG에너지솔루션]반기검토보고서(2025.08.14).pdf|`a2efb0fb669fa9601b9a2886f99b6837fce27b2545e89000bc90a941960e8975`|
|[조선내화]연결감사보고서(2026.03.19).pdf|`8c2b59e4830901ed9455ce6ebe35f2269cbe93937004418c2df2daba1c45a41d`|

