## 한눈에 보기

### 1. 이번에 무엇을 했나?
기존 작업을 재점검하며 발견한 제목 행 앞 원문 소실을 같은 해석기에서 수정했습니다. 정상 자료와 공식 원본도 다시 대조했습니다.

### 2. 실제로 무엇이 달라졌나?
제목 행 앞의 값과 공백 셀을 버리지 않고 원문·위치를 보존합니다. 잘못된 자료는 오류와 미확정 기록으로 남깁니다. 정상 언어 선언과 표시 이름·출처 구분은 유지합니다.

### 3. 확인 결과는 어땠나?
관련 검사 127건, 공개·합성 자료 전체 검사, 공식 원본 대조와 독립 검토가 통과했습니다. 기존 엄격 검사의 1건 실패·76건 건너뜀과 실제 자료 81건 부족은 남습니다.

### 4. 아직 남은 문제는?
검증 대상 회사·기간·최초/정정 정보와 당기 이름 공간 근거가 없습니다. 실제 보고서 적용·업무 사용과 원본 중복의 해석은 미확인입니다. 다른 풋팅 작업의 기준값 비교 실패도 그대로입니다.

### 5. 내가 결정해야 할 게 있나?
이번 보존 오류 수정에 추가 구현 승인은 필요 없습니다. 다음 실제 자료 확인에는 검증 대상과 기존 Excel 참조 양식을 확인해야 합니다. 회계 판단·보호 기준 변경·병합·업무 수용은 별도 결정입니다.

### 6. 지금 상태는?
사람 확인 필요. 승인된 기술 수정과 검증을 마쳤고 초안 검토를 기다립니다. 기본 제품 병합이나 업무 수용 완료로 표시하지 않습니다.

## Developer Details

Date: 2026-10-12. Issue #11 / existing draft PR #33. Source base `051a49c5347f8106ebfc67ff3782379793f41034`; main `6373a333414f51015f9d1068e32ec2ef7702cbe4`. Existing isolated worktree reused; original dirty checkout and #12/#18 work preserved. Original Issue instructions authorize implementation, checks, independent review and Issue/Dashboard/PR records; no merge/release authorization is inferred.

### Reproduction and minimal correction

Independent Reviewer found a nonempty row inserted before the Label language/header rows was silently discarded while `current_applicable=True` and diagnostics were empty. A second probe found whitespace-only extra metadata cells were also discarded after normalization. Both are source-preservation/header outcomes within the approved Issue #11/R6 parser scope, not accounting choices.

Recognize explicit A/B or B/D LinkRole/Definition metadata and the immediately preceding lexical language-marker row. Unknown pre-header cells retain exact raw text (including whitespace), every physical row/column and snapshot locator in UNRESOLVED source fields; no header/name/QName is invented. REJECTED_LABEL_ROW is ERROR and prevents current applicability. Invalid language preambles do not become resource authority. Normal ko/en, fr/en-US and both observed metadata layouts remain valid; this lexical check does not certify a registered language or namespace.

Parser version `/4`→`/5` invalidates stored interpretation identities. Only `taxonomy.py` changes in production. Add one 12-case fresh-OOXML module; two task-owned version assertions track `/5`. The eight approved V2-1 dependency files and original Taxonomy tests remain unchanged. No protected tests, samples, GATES, accounting rules, catalog/skip/threshold/timeout, legacy DB, #9 recommendation or #12 code changes.

### Fresh verification on the final source

| Check | Result |
| --- | --- |
| New preamble cases before original /4 fix | 7 FAIL / 2 PASS, exit1; actual loss reproduced |
| Intermediate /5 raw-metadata whitespace probe | 1 FAIL / 1 PASS / 10 deselected; prior failure retained |
| Final explicit seven-module scoped suite | 127 PASS + 39 passing subtests; 0 FAIL/ERROR/SKIP; pytest39.47s / command45.047s |
| Same eight acceptance probes | PASS / exit0 |
| Final official source comparison | PASS / 71.462s; Labels30,909 + source fields9,467; zero exact tuple/raw-value/identity/header/location mismatches |
| Required strict `python -B scripts/test_auditdesk.py` | FAIL / exit1 / 109.099s; 229 PASS / 1 FAIL / 76 SKIP; same missing `_KNOWN_GENERATIONS`; web build PASS |
| Required `python -B scripts/test_all.py --timeout 600 --report <evidence>` | Technical Gate PASS / exit0 / 602.405s aggregate; Python225 PASS (38.96s), webPASS (11.95s), unchanged DSD public4/4PASS (550.07s) |
| `python -B scripts/check_protected.py --base origin/main`; `git diff --check` | PASS / exit0 |
| Independent final review | PASS / 0 unresolved blockers; five independent boundary probes; final raw source/scoped/strict/protection/aggregate records inspected |

The aggregate applies the unchanged600s maximum to each component. The external900s process bound covers their sum, not a relaxed component gate. Total602.405s is consistent with completed component bounds. Scope overlap is not an additive count of unique tests. The aggregate does not collect these new auditdesk/tests, so the explicit scoped suite is required separately.

Exact test command: `python -B -m pytest --noconftest -p no:cacheprovider auditdesk/tests/test_xbrl_v2_taxonomy.py auditdesk/tests/test_xbrl_v2_taxonomy_integrity.py auditdesk/tests/test_xbrl_v2_taxonomy_official_layout.py auditdesk/tests/test_xbrl_v2_taxonomy_label_provenance.py auditdesk/tests/test_xbrl_v2_taxonomy_label_preamble.py auditdesk/tests/test_xbrl_v2_core.py auditdesk/tests/test_xbrl_v2_offline.py -q -rfEs --junitxml=<evidence>`.

The exact official workbook bytes retain SHA-256 `d7135781ed425bb2e43a7dafffc3189435bbd16a70fae3d98c258ea8dc9845e7`. Final records: Concepts9,451 / Roles2,004 / occurrences68,898 / Labels30,909 / References6,267 / provenance9,467. PARTIAL, dimensions unknown, current_applicable=False remain intentional because report context/namespace evidence is absent. Duplicate/missing source identity and unknown abstract flags remain visible. Source preservation is not full path/DRS/accounting/applicability PASS.

Compatibility:81 BLOCKED: REQUIRED MATERIAL UNAVAILABLE; business PENDING. #18's separate candidate branch retains0/4 registered gatePASS and ten baseline metric deltas; this #11 aggregate does not resolve them. Actual report/extension/full DTS/DRS/editor/business acceptance NOT RUN or outside this bounded scope. The clarified output goal is an existing taxonomy+financial-number Excel reference; IXD generation is excluded and no new Excel template is selected here.

Evidence and raw-record SHA-256: [ISSUE11_TAXONOMY_PREAMBLE_EVIDENCE.json](ISSUE11_TAXONOMY_PREAMBLE_EVIDENCE.json). Independent cutoff and completion addendum: [ISSUE11_TAXONOMY_PREAMBLE_REVIEW.md](ISSUE11_TAXONOMY_PREAMBLE_REVIEW.md). Historical R1/R2/R5/R6 reports and failing records remain unchanged. New commit remote CI NOT RUN at this report cutoff; prior remote PASS applies only to head051a49c5.

Implementation hash scope: executed worktree CRLF SHA-256 `98ec425657662109f2bce09e49b11ad73d6e5c8c008e3af93027b4b127cc379f`; staged/Git LF SHA-256 `c6fb7da58c96bd7191df8c6738727a69d4147a7d8359091e0dbb5e7dc9771301`. Independent review proved identical bytes after CRLF-to-LF normalization. This is line-ending identity, not a product change.
