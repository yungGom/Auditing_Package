---
name: Development task
about: Define a verifiable change for an AI or human implementer
title: ""
labels: []
assignees: []
---

## 한눈에 보기

<!-- 업무 담당자가 30초 안에 이해할 수 있도록 쉬운 한국어와 짧은 문장으로 작성하세요. 개발 용어, 코드명, 함수명, 파일명은 아래 Developer Details에 적으세요. -->

### 1. 지금 무슨 문제가 있나?

<!-- 실제 현상과 그로 인해 업무에서 겪는 문제를 먼저 2~4문장으로 설명하세요. -->

### 2. 왜 업무상 문제인가?

<!-- 감사·회계·사용자에게 어떤 영향이 있는지 쉬운 말로 설명하세요. -->

### 3. 어떻게 해결하려고 하나?

<!-- 구현 방법 대신 해결 방향을 설명하세요. 꼭 필요한 기술 용어는 쉬운 한국어로 바꾸세요. 예: '시작 시점의 내용을 끝까지 그대로 사용하고, 새 파일이 완성된 뒤에만 기존 파일을 교체합니다.' -->

### 4. 내가 결정해야 할 게 있나?

<!-- '없음' 또는 '있음' 중 하나만 남기세요. '있음'이면 결정할 내용과 선택지별 장단점을 쉬운 말로 적으세요. 같은 결정의 기술 상세는 아래 Human decision required에 기록하세요. -->
없음 / 있음

### 5. 성공했다고 볼 기준

<!-- 사람이 결과를 보고 확인할 수 있는 기준을 짧은 문장 3~6개로 적으세요. 아래 Acceptance criteria와 모순되지 않아야 합니다. -->

- [성공 기준 1]
- [성공 기준 2]
- [성공 기준 3]

### 6. 지금 어디까지 됐나?

<!-- 하나만 남기세요. '완료 후보'는 사람의 최종 확인이 남은 상태입니다. 실제 검사 결과와 다르게 완료라고 쓰지 마세요. -->
준비 중 / 개발 중 / 테스트 중 / 사람 확인 필요 / 완료 후보 / 완료

## Developer Details

아래는 개발 계약과 검증 기록입니다. 기존 제목을 유지해야 Harness가 필요한 항목을 읽을 수 있습니다. 위 한국어 요약과 내용이 일치해야 합니다. Branch, PR, push, fixture, regression, baseline, snapshot, atomic publish, golden, orchestrator, Technical PASS 같은 표현은 원칙적으로 이 아래에만 적으세요.

## 이번 Issue에서 알아두면 좋은 용어

<!-- 이 Issue의 기술 상세에서 실제로 사용한 용어와 쉬운 뜻만 적으세요. 용어가 없으면 이 섹션 전체를 삭제하세요. -->

- 용어: 쉬운 뜻

## Problem

Project/component:
Problem or desired behavior:

## Business rule and owner

Business rule source and owner:

## Acceptance criteria

Use synthetic or public data only. Include normal, mismatch, missing, and ambiguous cases where relevant.

| Input | Expected result | Reason |
| --- | --- | --- |
| | | |

## Reproduction

Current behavior and exact reproduction command or steps:
Expected behavior:

## Protected artifacts affected

Data/offline boundary:
List protected paths or symbols from `governance/PROTECTED_ARTIFACTS.md` (or `none`):
Existing gate baseline and known exceptions to preserve:
Out of scope:

## Required tests

Automated commands and expected evidence:
Manual checks:

## Human decision required

Accounting judgment or protected-artifact decision (or `none`):

## Definition of done

Definition of done: implementation, applicable tests without hidden failures/skips, independent review, and human business acceptance.
