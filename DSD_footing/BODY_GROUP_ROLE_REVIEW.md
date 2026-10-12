## 한눈에 보기

### 1. 이번에 무엇을 했나?
남은 기준 차이를 기존 행별 근거로 분류하고, 표에 명시된 손익 구획을 역할 정보에 반영하는 누락을 보완했습니다.

### 2. 실제로 무엇이 달라졌나?
평가·처분 손익 구획 아래의 불명확한 역할에 원문 행 근거를 남깁니다. 자동 연결과 기존 검토 대상은 같습니다.

### 3. 확인 결과는 어땠나?
집중 검사와 독립 검토는 통과했습니다. 공개 자료의 연결 관계는 보완 전후 같습니다. 공식 기준값 비교는 네 건 모두 실패하며 종전 차이를 유지합니다.

### 4. 아직 남은 문제는?
의미와 범위 확인이 필요한 열두 금액 칸, 기준값 차이, 실제 업무 자료·화면 확인은 남습니다. 이번 보완을 회계 판단 확정으로 해석하지 않습니다.

### 5. 내가 결정해야 할 게 있나?
기존 검토 유지 결정은 그대로 적용합니다. 기준값을 갱신하려면 아래 전후 차이에 대한 별도 승인이 필요합니다. 권장 순서는 검토 대상 보존을 확인한 뒤 검사 수 변화와 자동 제외의 기준 반영 여부를 판단하는 것입니다.

### 6. 지금 상태는?
역할 정보 보완은 검증·독립 검토 완료입니다. 전체 기준 비교와 업무 수용은 미완료이며 초안과 열린 이슈를 유지합니다.

## Developer Details

Issue #18 / DSD-002 / existing draft PR #31, 2026-10-12. This supersedes the earlier statement that the FVOCI category parser role remains unresolved; it does **not** supersede Owner keep-review decisions or claim the ten metric deltas are fixed.

### Root cause and bounded change

The registered LGES public source table p29/t1 contains the explicit `평가손익/처분손익` physical row group. The category account name alone yielded no role and lost that displayed group evidence. `refmap.py` now uses only a standalone physical group row with empty other cells and no numeric values. New headings, blank separators and totals terminate ownership. Existing explicit roles and SCE review roles are preserved. Raw group label and zero-based extracted row index are retained as `role_source`, including review candidates.

`_role`, `_item_key`, `same_period`, value/period/unit/sign/tolerance guards and protected artifacts are unchanged. No company/page/value whitelist, title alias, OCI equivalence, zero filling or accounting composition assumption is added. New synthetic `test_body_group_role.py` covers positive ownership, raw label preservation, OCI non-equivalence, title-only rejection, ownership termination, mixed/numeric headings and BS/SCE controls.

### Remaining ten protected comparison deltas

| Sample | Metric before → after | Evidence classification |
| --- | --- | --- |
| Samsung | C_ok 51 → 46; C_unmatched 56 → 61 | Same five cells: two flow-versus-prior-stock exclusions and three financing net/gross/same-item reviews |
| Humax | A_total 567 → 572; A_SKIP 48 → 53 | Five audit headcount/time A1 exclusions retained as SKIP |
| LGES | A_total 395 → 397; A_OK 379 → 381 | Two valid small displayed interest checks restored |
| LGES | C_ok 82 → 75; C_unmatched 33 → 40 | Same seven cells: five existing OCI Owner reviews and two financing scope reviews |
| Chosun | A_total 380 → 384; A_SKIP 29 → 33 | Four audit headcount/time A1 exclusions retained as SKIP |

Thus A expands by eleven records: two OK and nine SKIP. The old Humax shareholder-ratio defect was already fixed and is not a remaining delta. The four C metric deltas double-count twelve main cells, not twelve new product defects. Stronger source composition in two OCI cases never overrides prior review status; the three period-limited FVOCI cases remain insufficient-evidence review. No newly confirmed defect explains these deltas. Any future baseline decision must be confined to the displayed exact before/after and preserve the twelve review cells. Existing baseline FAIL remains until a separate Owner decision; no update command was executed.

### Executed evidence

- Before fix: eight synthetic methods, three FAIL/five PASS; missing group role reproduced.
- `python -B -m unittest discover -s DSD_footing -p 'test_*.py' -v`: **63 PASS, 0 FAIL, 0 SKIP**, 30.640s test runtime, 35.366s wrapper.
- Read-only replay of identical cached extraction for four SHA256-identified registered public PDFs: **PASS**, 9.267s. Main-note coordinate-pair sets, unmatched main-coordinate sets and secondary link tuples are identical. LGES ten note role metadata entries and four review-candidate source entries are enriched. This is neither full-payload byte equivalence nor a fresh official gate.
- `python -B scripts/test_dsd_footing.py`: **0/4 PASS, 4 FAIL, 0 SKIP**, COMPLETED/exit1, 409.030s. Same ten protected comparison deltas above, no new metric difference and no baseline update. Overall Technical PASS is not claimed.
- `python -B scripts/check_protected.py --base origin/main`: **PASS**. `python -B DSD_footing/intake_check.py`: **PASS**. Whitespace check PASS.
- Independent reviewer: **scoped PASS / blocking 0**, eight small boundary controls PASS. Initial reviewer extra-text fixture used the `주석` keyword and hit the existing note-column exclusion; corrected final fixture passed. This was a probe setup error, not a product defect. No duplicate large gate run was performed by the reviewer.
- NOT RUN: separate GUI/drag-and-drop, private compatibility, all-page visual review, merge/deploy. Business acceptance **PENDING**.

### Hash and evidence identity

Executed worktree refmap SHA256: `19d2d99f2590b706bb9407624dc88de7b3986b21a1f0bfc647b9dc2d45322e86`. LF-normalized SHA256 for Git content: `c546d5fed6b2043d63b4fae51158c58d2e015c0dd5b6698afdbe6b8897e046ff`. The difference is newline representation only. Actual source samples remain unchanged. Structured sample outcomes, classifications and raw evidence digests are in `reviews/issue18-20261012/body-group-role-evidence.json`. No private F1-F3 input, original workbook, client path or client numeric content is included in this report.
