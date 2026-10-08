## 한눈에 보기

### 1. 이번에 무엇을 했나?
독립 검토자가 네 공개 자료의 예외 색인과 PDF 표시 누락 원인·수정을 확인했습니다.
### 2. 실제로 무엇이 달라졌나?
출력 문서에 먼저 페이지를 추가하고 페이지 내용을 분리한 뒤 표시를 합쳐, 뒷페이지 누락과 다른 페이지로의 표시 누출을 막습니다.
### 3. 확인 결과는 어땠나?
집중 검사 52개가 통과했습니다. 검토한 수정 범위의 출력 차단점은 해소됐습니다. 공식 비교 결과와 업무 수용은 별도입니다.
### 4. 아직 남은 문제는?
12칸은 미성립·검토 상태입니다. PDF에는 주석 연결 미성립 전용 물음표가 없으므로 예외 색인과 함께 확인해야 합니다.
### 5. 내가 결정해야 할 게 있나?
추가 결정 요청은 없습니다. LG엔솔 세 기간의 기존 결정을 유지합니다.
### 6. 지금 상태는?
변경 범위 독립 검토 완료. 최종 공식 실행 증거와 함께 Owner Review에서 멈춰야 합니다.

## Developer Details

Reviewer: `/root/issues27_30_review`, independent read-only pass, 2026-10-08. Scope: output follow-up after source-context base e15e69a. Final product scope findings: blocking0. This is not a claim that the official baseline gate passes or that every accounting relation is accepted.

- Actual initial XLSX: every six-column C-sheet row compared as an exact multiset against final source-context diagnostic. Samsung107=46/61; Humax82=67/15; LGES115=75/40; Chosun80=35/45. Total384 rows. Specified12review cells retain 미성립, reasons and candidate coordinates. LGES OCI rows98/101/102/103/104 include the Owner's three insufficient periods. Samsung duplicate treasury amounts remain separate rows89/90; main-period/column export limitation remains.
- Blocking finding reproduced: actual Humax p167 original and output content bytes initially identical although cached production prefix produced16SKIPmarks plus footer. Old source-page merge followed by writer.add_page dropped the destination overlay because an earlier internal link cloned that future page first. Two-page synthetic forward-link case reproduces it. Holding overlay readers alive alone does not fix it.
- Fix independently inspected and executed: writer-owned page before merge; detach shared contents to prevent sibling-page mark leakage. Reviewer command from `DSD_footing`: `python -B -m unittest test_pdf_output test_source_context test_followup test_issue27_30 -q`:52PASS (30.716s). Includes forward-destination link preserved, shared-stream negative controls,168-page unique overlay delivery and no-overlay source preservation. Root's separate discovery invocation is recorded in output-review.json.
- Independent actual Humax168page in-memory control with one marker: marker found only on p167; adjacent p166/p168 content bytes identical to source.
- Final diagnostic evidence: four PDF SHA256 values match `pdf-fix-verification.json`; totals433source pages and395overlay pages. Fixed Humaxp167 and Chosunp75 each have exactly17question marks (16arithmetic plus one footer), candidate-only footer and unchanged MediaBox. After removing added marks/footer, original body token counts match exactly. Normalized footer timestamps when comparing independently regenerated overlays.
- Root separately observes a fresh official-run Humax PDF and runs the official four-sample entrypoint. The final result belongs in `OUTPUT_REVIEW_OWNER_REVIEW.md` and `output-review.json`; reviewer does not infer it from synthetic or cached controls.
- Initial PDF defect is resolved in reviewed scope. Existing lack of dedicated C-unmatched PDF question marks and absence of main-period/column fields in C-sheet remain explicitly documented limits. No baseline/rule/threshold/public sample changes or automatic-link expansion reviewed or authorized here.
