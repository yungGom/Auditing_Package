## 한눈에 보기

### 1. 이번에 무엇을 했나?
승인받은 네 문제를 기본 코드의 별도 사본에서 수정하고, 수정 전후를 합성 자료로 비교했습니다.
### 2. 실제로 무엇이 달라졌나?
작은 금액도 산술검사합니다. 본표 금액은 선언 단위를 맞춰 비교하며, 다른 기간의 주석 금액을 연결하지 않습니다. 산술검사 0건은 오류 대신 제한된 분석으로 안내합니다.
### 3. 확인 결과는 어땠나?
합성 검사 11개와 보호 대상 검사는 통과했습니다. 독립 검토의 세 코드 문제도 보완했습니다. 등록 공개 자료의 기존 기준과 집계가 달라져 비교 검사는 실패했습니다.
### 4. 아직 남은 문제는?
기간 없는 연결 제외 등에 따른 집계 변동의 원인과 업무 영향을 확인해야 합니다. 기존 기준은 그대로이며, 전체 검사 통과와 실제 업무 수용은 미확정입니다. 상위 조사에서 근거부족으로 남긴 8개 항목은 이번 수정 대상이 아닙니다.
### 5. 내가 결정해야 할 게 있나?
있음. 변경된 공개 자료 결과를 검토해야 합니다. 기존 기준을 바꾸려면 정확한 변경 내용에 대한 별도 승인과 운영 절차가 필요합니다. 이번에는 기준 변경이나 병합 승인을 요청 범위에 포함하지 않았습니다.
### 6. 지금 상태는?
사람 확인 필요. Owner Review에서 멈춥니다. 병합·배포·Issue 종결을 하지 않습니다.

## Developer Details

Source of truth: #18 / DSD-002, children #27–#30. Direct Human Owner approval in current chat (2026-10-02) transcribed into all five Issues. Approval covers investigation classification and implementation/tests/independent review; excludes final acceptance, merge, deployment and protected baseline mutation.
Baseline: remote main `6373a333414f51015f9d1068e32ec2ef7702cbe4`. Branch `codex/dsd-issues27-30`, isolated checkout. Original dirty checkout and dirty historical remediation worktree preserved. Changes authored as focused patches; no legacy product files copied wholesale.

### Changed behavior

| Issue | File / function | Before | After |
|---|---|---|---|
|#27|core.is_note_col/grid_info|Comma-free values below100 treated as note numbers even under amount header|Explicit note/reference/sequence/percentage headers excluded; small values alone do not exclude an amount column|
|#28|tieout.collect/add; final B workbook sheet|Raw amount comparisons ignored different declared units|Declared won/thousand/million/hundred-million converted to won before B1–B10 arithmetic; unknown/unsupported unit remains None/unverified. Original signs and exact comparison threshold retained. Workbook labels values as won and includes evidence|
|#29|refmap.column_periods/same_period/collect/build|Note matches based on unit-adjusted amount and reference, no period guard|Require matching explicit current/prior, span, half/quarter and date tokens; conflicting span/cadence unknown. Near-difference and secondary-note links also period guarded. Missing identity remains unmatched, not zero|
|#30|final summary/console|Zero denominator raised after outputs created|Safe ratio, visible limited-analysis warning including --quiet, workbook analysis-status row. Zero checks never described as arithmetic verification complete|

Unit association is bound to the processed first table. Continuation is retained only for single-table pages; ambiguous unprocessed extra tables cannot inherit that unit. This conservative restriction may expose missing B coverage instead of a false OK. No tolerance, accounting formula, threshold, EXCL_TABLE, verdict, A5_RULES, MIN_WON or protected artifact changed.

### Automated evidence

All commands use bundled Python `C:/Users/moonyong/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` as `python`, from the isolated checkout root. No dependency/manifest change; installed pdfplumber0.11.9 used.

- Before: `python -B -m unittest discover -s DSD_footing -p test_issue27_30.py -v`: 8 methods, failures10/errors1 including subtests. This was recorded before product edits; small amount, units, swapped/unknown period and zero-count CLI fail. Correct-period/nonamount controls pass. Log `../before27-30.log`.
- Final focused: same command: **11 methods PASS**, including7 unit subcases,9 nonamount headers,4 explicit date/span/cadence mismatches, positive controls and zero-count normal/quiet. Log `../after27-30-v3.log`. Test PDF font is Windows Malgun; execution evidence applies to this Windows environment, not unrun platforms.
- `python -B scripts/check_protected.py --base origin/main`: **PASS**, `../protected27-30-v3.log`. No baseline waiver or checker allowlist widening.
- `python -B DSD_footing/intake_check.py`: **PASS**, source signatures preserved.
- `git diff --check`: **PASS**.
- `python -B scripts/test_dsd_footing.py`: final run recorded in `../gates27-30-v3.log` and exit file. Pending final full output at this checkpoint; an earlier partial run was interrupted to resolve independent findings. That partial run is not final verification.
- `scripts/test_all.py`: **NOT RUN**, no shared/Harness/AuditDesk change, project-local gate is required and executed. No repository-wide Technical PASS claimed.
- Render golden, GUI/manual accounting UAT, Linux execution, actual-material compatibility: **NOT RUN**. No private client data used.

Baseline observation from original Issue18 main audit: registered four public PDFs **4/4 PASS**, 96 metrics unchanged before these fixes. New focused reproductions establish defects missed by those snapshots. A changed gate count is still a failing required comparison until separately reviewed and resolved; it must never be silently updated or relabeled PASS.

### Independent review

Reviewer `/root/issues27_30_review`, read-only, inspected contract/diff/tests and synthetic counterexamples.
Blocking1: initial period guard collapsed different explicit years, half/quarter and conflicting3M/cumulative. Fixed by preserving explicit date/cadence and rejecting conflicting signals. Independent three PDF cases now link1/unmatched1 (invalid current rejected, valid prior preserved).
Blocking2: initial carry used last unprocessed table with first-table unit. Fixed by only carrying processed single-table data; independent synthetic mock confirms unsafe rows are excluded. Persistent regression added.
Code blockers remaining: **0**. Reviewer independently ran the final11-method suite PASS, adversarial3PDF+1mock PASS and additional percentage-scenario/rate-header controls PASS. Implementing-agent final suite also has11methods PASS. Reviewer did not rerun full official gate and does not approve its changed baseline.

### Owner review and remaining limits

These are local branch fixes, not current-main completion. Child Issues remain open. #18 historical classification remains a dated main audit; four residuals become completion candidates only on this branch. #8/PR10 export flow remains separate and unchanged. Eight evidence gaps remain open.
No protected edit proposed/applied merely to pass tests. Any necessary GATES update is a separate exact-diff Owner decision, with per-sample before/after evidence. Current required-check protection cannot be bypassed with an approval comment; no settings/checker/admin bypass change is authorized here.
Dashboard fields and child unique Request IDs remain manual registration work; no duplicate parent ID assigned or automatic Done claimed.

### Code-free acceptance examples

1. Use a synthetic PDF with an amount table10+20 and total40, different unit BS/CF, or swapped current/prior note amounts.
2. Run the existing report launcher/CLI and open the exception-index workbook, checking A, B and C sheets.
3. Expect the small amount difference, unit-aware comparison and unmatched swapped period; a no-arithmetic PDF must show limited analysis instead of a division error. Human operator execution **NOT RUN**.

Rollback: switch back to the unchanged main baseline (`git switch --detach 6373a333414f51015f9d1068e32ec2ef7702cbe4`) after committed review work is preserved; no destructive reset required.

Third resolved regression: intermediate #27 percentage-header guard also excluded monetary scenario columns (10% 상승시/하락시, 할인율 0.25%증가/감소). Public Humax A_OK514→509/A_SKIP48→53 exposed it. Revised guard keeps scenario amount columns while excluding actual rate headers; four scenario subcases and no-percent interest-rate control added. Intermediate gate logs are interrupted checkpoints, not final evidence.


