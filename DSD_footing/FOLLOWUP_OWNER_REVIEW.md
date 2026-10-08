## 한눈에 보기

### 1. 이번에 무엇을 했나?
기간 해석과 빠졌던 비율 합계 검사를 보완하고, 의미가 다른 비교를 검토 대상으로 유지했습니다.
### 2. 실제로 무엇이 달라졌나?
표의 위치와 기간 근거를 확인하고 잔액과 거래액을 구분합니다. 확인할 수 없는 연결은 예외 색인에 후보 위치와 함께 남깁니다. 비율 합계는 금액 대사와 분리합니다.
### 3. 확인 결과는 어땠나?
합성 검사와 보호 대상 검사는 통과했습니다. 공개 자료 네 건은 모두 기존 기준과 집계가 달라 비교 검사가 실패했습니다. 전체 통과나 업무 수용을 확정하지 않습니다.
### 4. 아직 남은 문제는?
자동 연결 감소의 업무 영향을 확인해야 합니다. 날짜 근거의 출처 표시에도 제한이 있으며, 화면과 실제 업무 자료의 검사는 미실행입니다.
### 5. 내가 결정해야 할 게 있나?
있음. 검토 대상으로 남은 비교와 공개 자료 변동을 업무 관점에서 확인해야 합니다. 근거가 없는 비교는 미검증으로 유지합니다. 이번 결과로 기존 기준 변경을 권고하지 않습니다.
### 6. 지금 상태는?
사람 확인 필요. Owner Review에서 멈춥니다. 병합·배포·종결을 하지 않습니다.

## Developer Details

2026-10-04 implementation follow-up for #18 and #27–#30, draft PR #31, branch `codex/dsd-issues27-30`. Main base remains `6373a333414f51015f9d1068e32ec2ef7702cbe4`. Earlier investigation reports remain historical evidence, not current implementation results. Owner authorization includes fixes, checks and independent review; semantic mismatches remain review candidates. No protected edit or baseline approval is inferred.

### Implementation

- `core.py`: isolated A1 percentage sums restore supported composition/shareholder distributions. Independent subsidiary ownership and unknown denominators remain SKIP. Actual ratios stay excluded from monetary columns and B/C discovery, including million-won values above MIN_WON. Existing whole-source exclusions still apply; A2/A3/A5 and protected verdict/thresholds unchanged.
- `refmap.py`: bounded period tokens exclude measurement-category names; physical merged groups include excluded ratio columns. Above-table context uses horizontal and vertical ownership. Header continuation requires same known note section, adjacent pages, open donor, physical grid, position, column count and declared unit. Conflicts remain unknown. Side-specific supported fiscal dates are normalized; unbound single dates cannot identify both current/prior sides.
- Per-cell roles separate opening/closing balances from movements. Trusted BS balances and bounded financial-category/accrued/prepaid/allowance accounts retain balance identity; disposal gains stay movements. Differently named flows require human review even with equal amounts/periods. No amount-driven period recovery, unknown-to-zero conversion or sign relaxation.
- `final.py`: equal-amount rejected relations show a review reason and source candidate page/table/row/column in the exception index, rather than incorrectly claiming no equal amount exists. Rejected links get no normal C verification mark.

### Reproduction and focused checks

Bundled Windows Python used as `python`; UTF-8 output, no dependency or manifest changes.

- Initial follow-up reproductions failed before changes (`followup-before.log`). Six reviewer counterexamples reproduced as six failures (`followup-six-before.log`). Five balance-account misclassifications reproduced before final role correction (`followup-role-date-before.log`); the initial date test had a fixture collection error and was repaired before final checking.
- `python -B -m unittest test_followup test_issue27_30` from `DSD_footing`: **30 methods PASS** (19 follow-up +11 original), `followup-final-focused.log`. Includes positive and negative continuation, ratio, role, source geometry and period cases.
- `python -B scripts/check_protected.py --base origin/main`: **PASS**. Protected accounting definitions, samples, GATES and guides unchanged.
- `python -B DSD_footing/intake_check.py`: **PASS**. An earlier incorrect invocation under `scripts/` failed because that path does not exist; corrected project invocation passed.
- `git diff --check`: **PASS**.
- Public gate results and exact metric deltas follow below. No update flags or baseline replacement.
- `scripts/test_all.py`: NOT RUN, project-only changes. GUI/manual accounting UAT, PDF render comparison, private-material compatibility and Linux execution: NOT RUN. Public workbook inspection confirms Samsung's 21 equal-amount review rows include candidate coordinates; this is structure inspection, not accounting acceptance.

### Independent review

Reviewer `/root/issues27_30_review` independently executed all30 focused methods and additional balance-role, disposal-gain, unknown-date and positive side-anchor controls. All eight concrete blocking findings raised during this pass were fixed and independently rechecked. No remaining concrete code blocker in reviewed scope. Reviewer did not approve the official gate differences or business acceptance.

Reviewed SHA256: core `08B881A15B8E075DE04802374967DF60EC83AB3903CB6BEC4427CF228DE0FC64`; refmap `7E5FB50FC3E8D589ED186FE426D34C5326390BF6E657D70DAEF6A39B4D6A4A4A`; final `5AA721072F9F17F35122326F2AFF9C48A57F5C52BC6A99735A2FAA38CEA6C5CC`; follow-up tests `A4287CFF412C56084CFFD90784A6955750D8DF784B4396E97965116EE5026E94`.

### Limits and Owner Review

Date anchors/standalone dates contribute to period identity, but their source coordinates and raw text are not fully carried through to the workbook. Candidate table coordinates are available. Some legitimate differently named flows and ambiguous source layouts can remain unmatched; no target of restoring every lost link is imposed. Aggregate deltas do not establish row-level business correctness for every changed relation. Further public per-row review and manual accounting acceptance remain needed before any baseline proposal.

Issue #18's dated main classification remains one solved, four unresolved and eight insufficient-evidence topics. Branch fixes do not retroactively establish main completion. #28/#30 retain their prior fixes with the original11 regression methods executed; this follow-up primarily affects #27/#29. Issues remain open; draft PR remains unmerged. No merge, deployment, release or protected change authorized.

### Final registered public comparison

`python -B scripts/test_dsd_footing.py`: **FAIL, exit1; 0/4 PASS, 4/4 FAIL**, all registered public samples executed, no skips. Evidence `../followup-gates-final.log` and `../followup-gates-final.exit`. This run uses the independently reviewed final code hashes above. The earlier `followup-gates-first.log` is superseded intermediate evidence.

| Public sample | Metric | Protected baseline | Final branch |
|---|---|---:|---:|
|Samsung|C_ok|51|30|
|Samsung|C_unmatched|56|77|
|Humax|A_total|567|572|
|Humax|A_OK|514|513|
|Humax|A_SKIP|48|54|
|Humax|C_ok|67|52|
|Humax|C_unmatched|15|30|
|LGES|A_total|395|397|
|LGES|A_OK|379|381|
|LGES|C_ok|82|43|
|LGES|C_unmatched|33|72|
|Chosun|A_total|380|384|
|Chosun|A_SKIP|29|33|
|Chosun|C_ok|35|23|
|Chosun|C_unmatched|45|57|

15 changed metrics; all other registered metrics unchanged according to the executed comparison. C linked235→148 and unmatched149→236 out of384 main items. Conservative period/role identity exposes more unverified comparisons; the counts alone do not distinguish valid rejection from lost eligible coverage. No claim that every change is expected or accepted. A ratio restoration, exclusions and small-amount additions have focused controls, but final public row-level adjudication remains outstanding. Required comparison remains failed; no overall Technical PASS, baseline replacement or merge recommendation.
