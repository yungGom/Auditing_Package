## 한눈에 보기

### 1. 이번에 무엇을 했나?
실제 실행 경로에서 입력 오류, 검사 0건 안내, 작은 금액 차이, 출력 폴더 지정과 실패 상태 전달을 확인했습니다. 손상된 PDF와 Python 부재 상황도 추가 확인했습니다.
### 2. 실제로 무엇이 달라졌나?
Windows 실행 파일이 분석 실패를 성공으로 바꾸던 문제를 수정했습니다. 일시정지 화면이 있어도 분석 결과의 실패 상태를 그대로 전달합니다.
### 3. 확인 결과는 어땠나?
앞서 집중 검사 55개와 실행 시나리오 12개를 확인했습니다. 이번 추가 오류 시나리오 여섯 개도 기대한 결과와 일치했습니다. 직전 공식 공개 자료 비교는 네 건 모두 실패했고, 기존 지표 차이는 그대로 남습니다. 이번에는 제품 코드 변경 없이 추가 실행 검증만 했습니다.
### 4. 아직 남은 문제는?
검토 대상 12칸과 LG엔솔 세 기간은 그대로 미검증입니다. 별도 화면·끌어놓기 동작, 실제 업무 자료와 전체 페이지 시각 검토는 이번 확인 범위 밖입니다.
### 5. 내가 결정해야 할 게 있나?
추가 승인은 요청하지 않습니다. 기존 회계 판단, 자동 연결 범위와 기준값을 유지했습니다.
### 6. 지금 상태는?
사람 확인 필요. 기존 검토 요청에 반영하고 Owner Review에서 멈춥니다. 병합·배포·기준 변경·요청 종결은 하지 않습니다.

## Developer Details

Date:2026-10-08 Asia/Seoul. Issue#18 historical item7 (failure-state delivery), existing draft PR#31. Source-context/output base356bc72067bf7fdd5633ed8cc6935649fcceaf2f. User acknowledged the preceding report and requested continued work. This authorizes follow-up verification/fix, not a protected baseline change, merge, deployment or blanket accounting acceptance.

### Main reproduction and classification

- The diagnostic main export's ten relevant engine/entrypoint files were compared by Git blob identity to origin/main6373a333414f51015f9d1068e32ec2ef7702cbe4 before execution. Missing synthetic file: direct `foot.py` exits2 with a missing-file message; main `run.bat` with FOOT_NOPAUSE=1 reports the same error but exits0. Full identities and observed exits are in `reviews/issue18-20261008/entrypoint-review.json`.
- Same failure on the pre-fix implementation branch in both pause modes: engine2→batch0. Thus historical item7 is no longer insufficient evidence for the Windows CLI/batch failure propagation path: unresolved on tested main, fixed and verified only in the candidate branch. This does not claim that main is updated or that a separate GUI failure-delivery mechanism is fixed. Other historical UI/recovery/cache topics with no corresponding main API retain their previous insufficient-evidence classification.
- Existing report history remains intact. This bounded update does not rewrite prior C87-cell82/2/3 source classification,75restored links,12remaining reviews or LGES Owner choices.

### Root cause and minimal change

`run.bat` had no explicit exit after Python. Its final conditional pause/IF handling could replace ERRORLEVEL with0. Add `setlocal`, save `%ERRORLEVEL%` immediately after the Python invocation on a separate line, and return that saved value after optional pause. Three added lines, ASCII/noBOM. No changes to CLI arguments, engine modules, PDF/XLSX content, accounting identity/period/unit/sign/rounding rules, samples, GATES or thresholds.

### Reproduction and verification

- New `test_entrypoint.py`: missing-input usage2; missing-file failure2 in both pause modes; normal zero-check run0 with explicit limited-analysis message and PDF/XLSX files using a path containing spaces. Before fix:3methods executed,2failing subtests (both missing-file pause modes). Final root focused `python -B -m unittest discover -s DSD_footing -p 'test_*.py' -v`:55PASS,0FAIL,0SKIP,exit0. Existing52methods remain in the run.
- Actual entrypoint UAT initially12scenarios:10expected,2failures identifying the launcher bug. Eight CLI scenarios:help,missing input,missing file,wrong extension,textless PDF refusal,zero-check normal,zero-check quiet,small amount10+20≠40 with custom spaced output folder. CLI outputs and XLSX check results remain valid because the engine/CLI source did not change. Four Windows scenarios:usage without arguments,two failure pause modes,normal paused run. After fix the two failed batch scenarios and normal paused run were re-executed; usage was rechecked by the new focused/independent test. This is combined12-scenario coverage, not a claim that all12were rerun after a launcher-only edit.
- Small-amount case emits a visible A exception:display40,calculated30,차이. Zero-check normal/quiet runs exit0 while console and XLSX say 제한된 분석: 산술검사0건. They do not imply completed arithmetic verification. Missing/wrong-extension/textless input is rejected with exit2. No private input was used.
- Required fresh `python -B scripts/test_dsd_footing.py`:0/4PASS,4/4FAIL,0skips,exit1. Exactly the same ten metric deltas as the preceding PDF output review. Baselines unchanged. Product file hashes match the frozen pre-run values. No overall Technical PASS.
- `python -B scripts/check_protected.py --base origin/main`:PASS. `python -B DSD_footing/intake_check.py`:PASS. `git diff --check`:PASS. Required gate and focused logs are retained locally; their SHA256 values are committed in the evidence JSON.

### Independent review and limits

Reviewer `/root/issues27_30_review` independently reproduced both pre-fix failures, inspected the three-line batch change and ASCII/noBOM, then executed `python -B -m unittest test_entrypoint -v` from DSD_footing:3PASS,61.184s. Missing input2, missing-file2 in both pause modes, spaced-path normal0 and limited-analysis outputs preserved. No blocking finding in the reviewed launcher scope. Independent full55/official gate rerun is not claimed; those are root execution evidence.

The tests invoke actual `cmd.exe`, `run.bat` and bundled Python. They are scripted Windows CLI/launcher UAT, not OS drag-and-drop or a GUI session. Generic engine exit1, missing Python9009, Linux, private-material compatibility, separate GUI and all433pages visual inspection remain unverified. Previous selected11-page PDF review and all expected overlay-text/question-mark preservation remain separate evidence in `OUTPUT_REVIEW_OWNER_REVIEW.md`; no PDF change in this follow-up.

LGES three insufficient OCI periods and all12existing review cells remain unlinked. No new mapping alias, baseline approval or merge permission is inferred from the user's acknowledgement. Stop at Owner Review.

### Additional error-path UAT — subsequent continuation, 2026-10-08

The Owner requested further continuation after reviewing the published checkpoint. This evidence-only follow-up checks two previously unrun Windows cases; no product, test, sample, gate or accounting-rule files change. Evidence: `reviews/issue18-20261008/additional-failure-review.json`, based on source commit `3c1918b15d4dc4830c0b0cd3e5ff51127eb81014`. Root operator used actual `cmd.exe`, `run.bat`, bundled Python and a synthetic corrupt file with a spaced path.

| Scenario | Expected exit | Actual exit | Other observation |
| --- | --- | --- | --- |
| Corrupt synthetic PDF, direct CLI | 1 | 1 | PDFSyntaxError visible on stderr; no PDF/XLSX output |
| Same corrupt file, batch without pause | 1 | 1 | Same parser error; no output |
| Same corrupt file, batch with pause | 1 | 1 | Same parser error; no output |
| Python unavailable, batch without pause | 9009 | 9009 | Command failure on stderr; no output |
| Python unavailable, batch with pause | 9009 | 9009 | Command failure on stderr; no output |
| Python unavailable, no input argument | 2 | 2 | Usage remains visible; no output |

The missing-Python simulation restricts only child-process PATH to Windows System32. `where.exe python` returns1 before execution. It does not uninstall Python or change machine/user environment settings. This verifies launch-time command unavailability, not every installation failure. Corrupt input verifies one real engine exception path with exit1, not all possible internal exceptions. The existing raw parser traceback is observed, not a new friendly-error UI claim.

Root executed local diagnostic `python -B ../extra_failure_uat.py`. Independent reviewer `/root/issues27_30_review` executed the same diagnostic in memory with a separate output directory: all6cases matched, no PDF/XLSX outputs, source hashes unchanged and root evidence unchanged. Final report/JSON review: blocking0, no correction required in this scope. Independent evidence is retained in `reviews/issue18-20261008/additional-failure-independent.json`. Fresh `python -B scripts/check_protected.py --base origin/main` and `python -B DSD_footing/intake_check.py`:PASS; `git diff --check`:PASS. These checks do not turn the prior required official FAIL into a pass.

Six additional scenarios match their expected exits. The six source/test hashes frozen in the preceding record remain unchanged. Previous focused55PASS and official0/4PASS,4FAIL,0skips,exit1 with ten deltas are retained evidence, not fresh reruns for this documentation-only follow-up. No overall Technical PASS. Other NOT RUN limits remain: OS drag-and-drop, separate GUI, private compatibility, Linux and all-page visual review. The earlier NOT RUN labels for missing Python9009 and generic error1 are superseded only for the exact scenarios above. LGES decisions and all12reviewcells remain unchanged. Stop at Owner Review.
