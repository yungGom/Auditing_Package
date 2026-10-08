## 한눈에 보기

### 1. 이번에 무엇을 했나?
남은 기준 차이를 업무 의미별로 정리하고 공개 자료 네 건의 PDF와 예외 색인을 다시 생성해 확인했습니다.
### 2. 실제로 무엇이 달라졌나?
PDF 저장 과정에서 뒷페이지의 표시가 사라지는 결함을 찾아 수정했습니다. 판단 기준과 미검증 분류는 그대로 유지했습니다.
### 3. 확인 결과는 어땠나?
집중 검사 52개와 독립 검토를 마쳤습니다. 네 자료의 원본 본문·페이지 크기와 미성립 기록이 유지되고, 예상한 PDF 표시도 보존됐습니다. 공식 비교는 기존 기준 차이로 네 건 모두 실패했으며 기준은 바꾸지 않았습니다.
### 4. 아직 남은 문제는?
의미 확인이 필요한 12칸은 미검증·검토 대상으로 남습니다. PDF에는 주석 연결 미성립 전용 물음표가 없으므로 예외 색인을 함께 봐야 합니다. 전체 페이지 시각 검토와 실제 화면·업무 자료 확인은 미실행입니다.
### 5. 내가 결정해야 할 게 있나?
추가 승인은 요청하지 않습니다. LG엔솔의 세 기간과 기존 검토 대상을 유지하며 자동 연결 확대나 기준 변경을 하지 않습니다.
### 6. 지금 상태는?
사람 확인 필요. Owner Review에서 멈춥니다. 병합·배포·기준 변경·요청 종결은 하지 않습니다.

## Developer Details

Date: 2026-10-08 Asia/Seoul. Source-context base: e15e69ad62676604ac0fad3540a8c0e4bcfd86c4; output-only follow-up hashes in the evidence JSON. Scope: Issue #18 and existing draft PR #31. `final.py` delegates PDF writing to new `pdf_output.py`; accounting rules, thresholds, public samples and GATES are unchanged.

### Baseline differences by business meaning

|자료|기존 기준 대비 남은 변화|원문에 따른 분류|
|---|---|---|
|삼성전자|C51→46, 미성립56→61|자기주식 취득 거래액과 전기말 잔액 2칸은 적절한 자동 연결 제외. 차입금 순증감/상환과 재무활동 변동 3칸은 순액·총액·계정 범위 확인 전 검토 유지.|
|휴맥스|A_total567→572, SKIP48→53|물리적 p167 감사 투입 인원·시간 표의 새 A1 후보 5건. 금액 합산 대상으로 확정하지 않고 기존 제외 판단을 가시화. p16 주주 구성비 합계는 OK로 복구됨.|
|LG엔솔|A_total395→397, OK379→381; C82→75, 미성립33→40|p59/60 특수관계자 이자비용 34/20백만원 합계 2건은 유효한 누락 검사 보완. OCI 5칸과 차입금 범위 2칸은 검토 유지. 사용자가 선택한 세 OCI 기간은 근거 부족 상태를 유지.|
|조선내화|A_total380→384, SKIP29→33|물리적 p75 감사 투입 인원·시간 표의 새 A1 후보 4건. 금액 검사로 인정하지 않고 미검증 유지.|

Ten registered metric differences; all other metrics retain the frozen official results. Added SKIP9 and valid interest OK2 are observed behavior changes, not permission to update protected baselines. The 2026-10-06 arithmetic ledger records historical payload deltas; its A01 Humax OK→SKIP is fixed in current product and is not a remaining regression. Current cached production-loop evidence is local `arithmetic-source-check.json`.

### Actual output verification

- Initial actual full generation: bundled Python `-B DSD_footing/final.py <registered sample> --tol 0 --out <task output directory>`, all four registered public samples. Four subprocess exits0 and all eight files exist. This exposed a PDF merge defect despite successful exits and correct financial metrics. Exit0 alone is not output acceptance.
- Corrected persistent PDFs: current production prefix with identical SHA-identified cached extraction produces all expected overlays; production helper merges them into actual original PDFs. Every page is checked for complete expected overlay text and question-mark counts, as well as unchanged source text. Actual full-run XLSX files are retained since financial/export behavior did not change. This cached diagnostic is explicitly separate from the fresh official runner, which performs real extraction and actual full output generation.
- Observe actual fresh official Humax output before temporary cleanup: physical p167 has16 arithmetic question marks plus one footer question mark and the candidate-only footer. A copy/hash is retained locally; observation is recorded in the evidence JSON. Thus the fix is also observed in a real-extraction full-run PDF, not only cached diagnosis.
- Read-only `check_generated_outputs.py`: compare every C-sheet row against final cached source-context relations, including multiplicities; require review reason and candidate coordinates. Totals:223성립/161미성립 over384 referenced main amount cells. All12 designated review cells remain unlinked; duplicate Samsung treasury entries remain separate rows.
- For every page of all four PDFs, verify original extracted text is retained and MediaBox/page count is unchanged. This checks structural preservation, not visual placement on every page. Version stamp e15e69a, tolerance0, round_steps1 and min_won100000000 preserved in all four workbooks. Source/output hashes and exact XLSX row coordinates are in `reviews/issue18-20261008/output-review.json`.
- Visual review by implementer: rendered Samsung physical p14/15/79; Humax p16/167; LGES p8/10/29/59/60; Chosun p75 using bundled Poppler. Selected pages cover retained OCI/financing reviews, shareholder ratio, restored interest checks, continuation source and extra excluded audit-time checks. This is selected-page output review, not all-page certification or app UAT.
- Poppler prints missing display-font alias notices for Symbol/ArialUnicode. Inspected PNGs show legible source Korean/numbers and overlays; source text retained. No font substitution or original PDF edit performed.
- Initial PowerShell log redirection treated bracketed public filenames as wildcards and prevented three invocations. Stale `$LASTEXITCODE` values from that loop are invalid evidence. Re-executed those samples using literal Python subprocess paths; `generation.json` records actual exits and file existence. No product fix was needed.

### Output limits and review boundary

- `final.py` exports C unmatched as 미성립 with review_reason and candidate coordinates in the C sheet. It does not draw a dedicated `?` for every C-unmatched amount in the PDF. Existing arithmetic SKIP marks and reference circles have different meanings. Do not interpret the absence of a C circle or the presence of a row-total arithmetic tick as C verification.
- C-sheet main columns/periods are not separate export fields. Same-value Samsung treasury entries have two rows but similar display labels; use the retained diagnostic source coordinates for distinction. No export-format expansion is included in this evidence follow-up.
- LGES OCI current3M−7,533, prior3M213 and prior cumulative1,650 million won remain Owner-selected insufficient-evidence reviews. Current cumulative−10,154 and defined-benefit cumulative1,030 retain prior review despite stronger source composition evidence. Financing scopes and treasury exclusions also retain review.
- Fresh focused52PASS (previous48 plus4 output controls). Fresh `python -B scripts/test_dsd_footing.py`:0/4PASS,4/4FAIL,0skips,exit1; exactly the same ten metric differences as source-context final-v2. Protected/intake/diff checks PASS. No shared suite/private compatibility/Linux/app GUI UAT or complete all-page visual review. No overall Technical PASS or business acceptance inferred.

### PDF delivery defect, reproduction and fix

An internal link on an earlier source page can cause PdfWriter to clone a later page before that page receives its overlay. The old source-page merge followed by add_page reuses the already-cloned unmarked contents. Actual Humax p167 and Chosun p75 lost arithmetic SKIP marks even though XLSX records and metric counts remained correct.

A two-page synthetic forward link reproduces the loss. A shared-content-stream fixture also reproduces wrong-page marks under the old algorithm; merely merging into writer-owned pages without separating shared contents can leak marks to sibling pages. `write_tickmark_pdf` first adds the source page, detaches that page's contents into a fresh stream, then merges into the writer-owned page. It preserves internal links and untouched pages. Four added tests cover forward links, shared streams and no cross-page marks,168-page distinct overlays, and no-overlay preservation. Before shared-stream control failed; final all52 methods pass.

Independent reviewer reproduced the actual Humax defect, confirmed the forward-link root cause, reran52PASS and verified a control mark exists only on actual p167 while adjacent p166/p168 contents remain byte-identical. No remaining blocking finding in this changed scope. All four final diagnostic PDFs also preserve every expected overlay's text/question marks; selected affected pages were re-rendered after the fix. This does not claim dedicated PDF C-unmatched question marks, which remain an existing export limitation.

Independent review evidence is recorded separately. Stop at Owner Review; no protected baseline update, automatic mapping expansion, merge, deploy or Issue closure.
