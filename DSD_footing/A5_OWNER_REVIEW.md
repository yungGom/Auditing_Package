## 한눈에 보기

### 1. 이번에 무엇을 했나?

명시된 지분법손익을 세전이익 계산에 한 번만 포함하고, 근거가 부족한 항목은 확인 대상으로 남기도록 보완했습니다. 사용자가 승인한 검사 집계도 함께 반영했습니다.

### 2. 실제로 무엇이 달라졌나?

보고서에서 기본 항목·금액·부호·기간을 확인할 수 없으면 정상이나 오류로 단정하지 않습니다. 계산·차이 칸은 비워 두고, 미검증 표시와 사유·원본 위치를 유지합니다. 사람이 정산표 등 별도 자료로 대체 검증할 수 있습니다.

### 3. 확인 결과는 어땠나?

집중 검사, 전체 반복 검사, 공개 보고서 비교와 원본 보존 확인은 통과했습니다. 보호 검사는 승인된 규칙과 기준 변경을 감지해 실패합니다. 이 실패를 숨기거나 검사 설정을 바꾸지 않았습니다. 원격 검사는 이 로컬 보고서 작성 시점에는 미실행이며 게시 후 별도로 기록합니다.

### 4. 아직 남은 문제는?

근거가 부족한 여섯 항목은 그대로 미검증입니다. 실제 회사 자료와 화면 검사는 완료되지 않았습니다. 필수 보호 검사에 사용자 승인을 반영하는 정상 절차가 아직 확인되지 않아 병합이 막힐 수 있습니다.

### 5. 내가 결정해야 할 게 있나?

이번 미검증 처리·검사 집계·커밋·게시와 DSD 수정 묶음의 병합은 승인됐습니다. 같은 승인을 다시 요청하지 않습니다. 보호 검사 실패를 무시하거나 정책을 바꾸는 승인은 없으므로, 정상 병합 절차가 막히면 그 대상과 이유를 별도로 알립니다. 실제 근거의 대체 검증은 사람의 업무입니다.

### 6. 지금 상태는?

완료 후보.

## Developer Details

Report type: implementation / local verification / Owner authorization checkpoint, before publication. Issue #18 continuation. New branch `codex/dsd-a5-equity-integration` starts from PDF-safe-save PR35 `060c6ecc2a4e2d376f2a45d60f8648877d24f68c`, which includes approved PR31 `81bff25d5d26f33126ae06dd491e07e1ccc11951`. New PR base is `codex/dsd-pdf-safe-save`; the new diff excludes all prior PR31/PDF-safe-save work. Existing dirty main-based A5, PR31, PR35 and XBRL worktrees are preserved.

### Owner decisions and exact protected diff

The original bounded rule implementation approval is Human `Sentinel_69241637db0481918ecf2ac8cfa23df4`. Subsequent Human `Sentinel_d9e6bd65d6e08191970d31c46ecb8932` approved preserving the six unknown items, the exact four metrics below, and committing/publishing them with the rule as a draft PR. Parent question `Sentinel_7597a41cee20819185802d8c51d91071` named those exact values and excluded merging. Human `Sentinel_39bffb54c2d881918349471fa41a3903` then expressly approved the DSD bundle's merge and intended practical use. [Issue approval transcription](https://github.com/yungGom/Auditing_Package/issues/18#issuecomment-6138612427) records the actual parent-supplied decisions; the bot does not impersonate a Human GitHub review.

| Public sample | Metric | Current approved PR31/PR35 | Approved new value |
| --- | --- | ---: | ---: |
| LG Energy Solution | A_total | 397 | 401 |
| LG Energy Solution | A_SKIP | 6 | 10 |
| Chosun Refractories | A_total | 384 | 386 |
| Chosun Refractories | A_SKIP | 33 | 35 |

Only these four leaves change in GATES. All other92metrics, tolerance0, recorded dates and metadata remain identical to current approved PR31/PR35. Main-only399/10 and382/31 are not imported. Applying/reversing these four changes restores the entire prior approved JSON exactly, preserving its ten previously approved changes.

One protected `A5_RULES` PBT entry adds explicit optional NET (`지분법손익`, `지분법이익(손실)`), GAIN (`지분법이익`) and LOSS (`지분법손실`) source-group metadata. Original five base terms and all other nine rules are unchanged. NET retains the source sign; nonnegative split gain adds and loss subtracts. NET+split overlap, duplicate physical rows (including blank rows), missing/ambiguous values, unclear signs or periods, unexplained/unsupported source rows, and possible base double inclusion fail closed. A clearly identified period remains independent of an ambiguous sibling; current/prior and three-month/cumulative identities are never borrowed. Unsupported aliases or separate impairment adjustments are not inferred.

Product diff: `statements.py`, one exception-output branch in `final.py`, GATES four leaves, and new `test_a5_equity.py`. This report is the fifth file. Existing tests, samples, `core.py`, `refmap.py`, `pdf_output.py`, other product rules, policy/manifest/checker/workflow/hooks are unchanged relative to PR35. Original A5 test content is identical after LF/CRLF normalization. Only the reviewed diff was imported, followed by intake verification.

`final.py` keeps unknown calculation/delta blank and existing reason text in the exception index. Existing reason-bearing SKIP rows may also gain their reason text in this same branch. This does not change their calculation or verdict; no claim is made that the entire XLSX payload is otherwise byte-identical. PDF source locations and generated question marks are retained. Unknown data is never zero-filled or marked verified.

### Six unknown cases

Page/row/column indices below are one-based physical PDF/table indices, including headers and the note column. All are table1. Each was previously NOT EMITTED and is now SKIP, n0, calcNone; displayed original values are not inferred.

| Public source | PDF / printed page | Row / column | Period | Confirmed missing basis |
| --- | --- | --- | --- | --- |
| LGES half-year report 2025-08-14 | 7 / 6 | 12 / 3 | 2025-04-01–2025-06-30, current3M | exact operating-profit anchor |
| LGES half-year report 2025-08-14 | 7 / 6 | 12 / 4 | 2025-01-01–2025-06-30, current cumulative | exact operating-profit anchor |
| LGES half-year report 2025-08-14 | 7 / 6 | 12 / 5 | 2024-04-01–2024-06-30, prior3M | exact operating-profit anchor |
| LGES half-year report 2025-08-14 | 7 / 6 | 12 / 6 | 2024-01-01–2024-06-30, prior cumulative | exact operating-profit anchor |
| Chosun consolidated report 2026-03-19 | 10 / 9 | 13 / 3 | 2025-01-01–2025-12-31, current | exact financial-expense base label |
| Chosun consolidated report 2026-03-19 | 10 / 9 | 13 / 4 | 2024-01-01–2024-12-31, prior | exact financial-expense base label |

LG's target is `Ⅹ. 법인세비용차감전순이익(손실)`. Source has `영업손실`, `기타영업외수익`, `기타영업외비용` and no explicit equity-method row. `ANCHOR_AMBIGUOUS` is missing anchor in this source, not a proven duplicate. These four are added unknown-coverage guards, not successful equity corrections or accounting errors. Chosun's target is `법인세비용차감전순이익`; `지분법손익` is present, but `금융원가` and separate `손상차손` do not establish the approved exact `금융비용` relationship. `BASE_MISSING_OR_DUPLICATED` is missing base here. No financial-cost alias or extra impairment subtraction is authorized.

### Executed local checks

| Exact entrypoint / scope | Result |
| --- | --- |
| `python -B -m unittest discover -s DSD_footing -p "test_*.py" -v` | PASS142, 0skips; 50.111s wrapper /46.520s suite; includes new44 +prior98 |
| `python -B scripts/test_all.py --timeout 600 --report <local evidence>` | PASS370.973s; selected technical checks3PASS /0FAIL /0SKIP /0NOT RUN |
| Aggregate Python technical partition | PASS225 /306collected /0collection errors, 28.03s;81real-material cases not selected by approved technical partition |
| Aggregate web build | PASS6.82s; locked npm install completed offline in19.769s |
| Aggregate `scripts/test_dsd_footing.py` | PASS4/4 registered PDFs,335.49s; all registered samples/tol0 compared; no update flag or skip |
| Actual one-page synthetic `final.py` CLI | PASS6.948s;2unknown PBT rows, calc/delta blank, n0, reason and question mark visible, source SHA unchanged |
| Fresh recognized A5 tables in first12pages of four public PDFs | PASS3.585s; exact6unknown locations/reasons and other9rule outputs preserved,4source SHAs unchanged; whole-page gate separately executed above |
| Current PR35 versus actual integrated A5 full C candidate dictionaries | PASS12cells,2.74s on SHA-identified frozen extraction; complete candidate multisets/reasons/labels/source values retained; not fresh candidate-object capture or entire workbook equality |
| `python -B DSD_footing/intake_check.py`; `git diff --check` | PASS |
| `python -B scripts/check_protected.py --base origin/main` | FAIL/exit1,9.029s; exactly `GATES.json(M)` and `statements.py:A5_RULES`; authorized diff, no checker exemption |
| Historical new44 tests against old pinned main sources | Prior evidence39FAIL/1ERROR/4PASS; the original rule defect/boundaries were reproduced without changing old expectations; not rerun in this checkpoint |

Default aggregate reports real-material compatibility as **BLOCKED: REQUIRED MATERIAL UNAVAILABLE,81cases**, material assessment only, and `human_business_acceptance=PENDING`. The Human's practical-use/merge decision is recorded separately; it is not fabricated execution evidence. GUI/UAT, private-company compatibility and full-page visual golden comparison are NOT RUN here. No actual company material is uploaded or committed. Public source or generated PDFs/XLSX and local raw evidence are excluded from publication.

Independent review inspects the final diff, count composition, rule/AST boundaries, tests and evidence. Its separately saved report records the bounded verdict and findings. It does not certify absent accounting evidence or waive protection.

### Merge route and version boundary

Current GitHub main protection requires `protected-artifacts` and `regression`, strict up-to-date checks, enforced for admins. Current checker compares to main and fails on any protected diff; no existing approval-aware waiver route was discovered in scripts/governance/workflow. Recording explicit Owner approval authorizes this reviewed commit/publication but does not make the checker PASS. No `--admin`, `--no-verify`, status fabrication, policy/manifest/hook/workflow/protection change or alternate bypass is used.

If protection remains red remotely, the DSD chain remains unmerged and the exact required normal-approval problem is returned to the Human Owner. A GitHub approval alone does not resolve a required failed status. The dependency order would begin with PR31→main, then retarget/revalidate PR35 and this A5 PR against the updated main; no child is merged into an already closed base branch as a workaround. XBRL PRs are outside the merge approval.

### Practical use of the reviewed candidate

After publication, use the exact commit reported in the PR. Until normal merging completes, this is the reviewed candidate branch, not an updated main release. Offline CLI entrypoint is `DSD_footing/foot.py` (or `run.bat`). With declared dependencies installed:

```powershell
python DSD_footing/foot.py "<PDF copy>" --tol 0 --out "<new output folder>"
```

Back up the original, run a copy into a separate new folder for each attempt, and retain prior completed output. Source PDFs are preserved. The inherited PR35 safe-save validates and publishes the PDF only after completion and preserves an existing completed PDF on failed save; this is not a whole PDF/XLSX transaction guarantee. Same-target concurrent PDF saves are blocked rather than mixed. Successful reruns may replace the same named output, so separate folders preserve prior runs. Stale saving claims require checking the owning run; do not delete another process's claim.

Keep `?`/미검증 and its reason; locate the source page/table/row/period and document manual alternative evidence separately (for example settlement schedule reconciliation). Do not interpret a regression PASS, absent report evidence or a matching inferred number as accounting verification. Filing/submission, deployment and external company-data upload are not performed.
