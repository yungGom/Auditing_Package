# -*- coding: utf-8 -*-
"""진성오류 선언 게이트 (C안) — 회계사 판정 선언과 실측 DIFF 집합을 대조한다.

왜 필요한가: GATES.json은 A_DIFF를 **골든으로 저장**한다. 도구가 오탐을 내면 그
숫자가 '정답'으로 굳고, 진짜 차이 1건이 사라지고 오탐 1건이 생겨도 건수가 같아
통과한다. 정답셋은 '회계사가 찾은 차이'라 도구만 틀린 오탐을 원리적으로 못 잡는다.

★ 이 모듈은 ERRORS.json을 **읽기만 한다. 쓰는 코드가 없다.** 갱신 플래그도 만들지
  않았다 — 갱신 경로가 없어야 손으로 고칠 수밖에 없고, 그것이 승인 절차다
  (2026-08-29 승인). gates.py의 --update-gates는 GATES.json만 건드린다.

실패 조건은 **양방향 집합 비교**다. 건수 비교로는 '진짜 1건이 사라지고 오탐 1건이
생김'을 못 잡는다:
    D − S ≠ ∅   미선언 DIFF 출현      → 회계사 판정 필요
    S − D ≠ ∅   선언됐는데 발화 안 함  → 고쳤으면 선언을 지워야 한다
"""
import json, os

ERRORS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ERRORS.json")


def _load():
    try:
        with open(ERRORS, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("[ERRORS] 경고: ERRORS.json이 없습니다 — 선언 대조 생략")
        return None
    except Exception as e:
        print(f"[ERRORS] 경고: ERRORS.json 읽기 실패 ({e}) — 선언 대조 생략")
        return None


def l1_key(page, check, disp, diff):
    """p{page}|{check}|{disp}|{diff}. 계정과목은 키에 넣지 않는다 — 라벨 열 선정이
    조판마다 바뀌고 '자 본 총 계'처럼 공백 변형이 있어 축을 늘릴 때마다 흔들린다."""
    return f"p{page}|{check}|{round(disp):d}|{round(diff):d}"


def l2_key(row):
    """{canonical_label}|{period_key}|{table_a}|{table_b}. 넷 다 회사 사전에서 온
    값이라 페이지·행 인덱스와 무관하다. 지분법손익 2건이 table_b로만 갈리므로
    넷 모두 필요하다(조선내화 반기연결 실측)."""
    return "|".join(str(row.get(k) or "") for k in
                    ("canonical_label", "period_key", "table_a", "table_b"))


def l1_keys_from_exc(exc_rows):
    """final.py의 exc(예외색인 행)에서 DIFF만 골라 키 집합을 만든다.
    행 구조: [page, table, kind, label, unit, disp, calc, diff, n, 판정, tag]"""
    out = {}
    for r in exc_rows:
        if r[9] != "차이":
            continue
        out[l1_key(r[0], r[2], r[5], r[7])] = r[3]      # 키 → 계정과목(표시용)
    return out


def _declared(entry, field):
    """선언 배열을 키 집합으로. reason/task가 비면 선언 자체를 거부한다 —
    사유 없는 오탐 선언은 '일단 통과시키자'와 구분되지 않는다(승인 조건)."""
    bad = []
    keys = {}
    for it in entry.get(field, []):
        k = (it.get("key") or "").strip()
        if not k:
            bad.append("key 없음"); continue
        if field == "known_false_positives":
            if not (it.get("reason") or "").strip():
                bad.append(f"{k}: reason 없음")
            if not (it.get("task") or "").strip():
                bad.append(f"{k}: task 없음")
        elif not (it.get("reason") or "").strip():
            bad.append(f"{k}: reason 없음")
        keys[k] = it.get("account") or it.get("verdict") or ""
    return keys, bad


def check(pdf, exc_rows, l2_res=None):
    """실측 DIFF와 선언을 대조. 통과·생략 True / 어긋남 False."""
    name = os.path.basename(pdf)
    doc = _load()
    if doc is None:
        return True
    entry = (doc.get("samples") or {}).get(name)

    found = l1_keys_from_exc(exc_rows)
    l2_found = {}
    if l2_res is not None:
        l2_found = {l2_key(r): r.get("canonical_label", "") for r in l2_res.get("confirmed", [])}

    # ── 선언 없는 축 ────────────────────────────────────────────────
    # '선언 0건'(판정 결과 없음)과 '선언 파일에 없음'(아직 판정 전)은 다르다.
    # 같은 실패로 뭉뚱그리면 회계사가 무엇을 해야 하는지 알 수 없다.
    if entry is None:
        if not found and not l2_found:
            print(f"[ERRORS] 대조 생략: '{name}' 선언 없음 · DIFF 0건 (판정할 것이 없음)")
            return True
        print("=" * 64)
        print(f"[ERRORS] *** 선언 없음: '{name}' ***")
        print(f"[ERRORS]   DIFF {len(found)}건 · L2 대사 쌍 {len(l2_found)}건이 나왔으나")
        print("[ERRORS]   이 축의 판정 선언이 ERRORS.json에 없습니다.")
        print("[ERRORS]   회계사가 전건을 진성/오탐으로 판정한 뒤 등록하십시오.")
        print(f"[ERRORS]   판정용 목록: python diff_list.py \"{pdf}\"")
        print("=" * 64)
        return False

    real, bad1 = _declared(entry, "accountant_confirmed_errors")
    fp, bad2 = _declared(entry, "known_false_positives")
    l2d, bad3 = _declared(entry, "l2_confirmed_pairs")
    bad = bad1 + bad2 + bad3
    if bad:
        print("=" * 64)
        print(f"[ERRORS] *** 선언 거부 [{name}] — 사유·과제번호 없는 선언이 있습니다 ***")
        for b in bad:
            print(f"[ERRORS]   {b}")
        print("[ERRORS] 사유 없는 선언은 '일단 통과시키자'와 구분되지 않습니다.")
        print("=" * 64)
        return False
    if not (entry.get("confirmed_by") or "").strip() or not (entry.get("confirmed_at") or "").strip():
        print(f"[ERRORS] 경고 [{name}]: confirmed_by/confirmed_at이 없습니다 — 누가 언제 "
              "판정했는지 추적할 수 없습니다")

    declared = set(real) | set(fp)
    undeclared = sorted(set(found) - declared)          # 실패 ①
    stale = sorted(declared - set(found))               # 실패 ②
    l2_undeclared = sorted(set(l2_found) - set(l2d))
    l2_stale = sorted(set(l2d) - set(l2_found))

    if not (undeclared or stale or l2_undeclared or l2_stale):
        print(f"[ERRORS] 선언 대조 통과 [{name}] — 진성 {len(real)} / 기지 오탐 {len(fp)}"
              + (f" / L2 대사 쌍 {len(l2d)}" if l2d or l2_found else "")
              + f" (판정 {entry.get('confirmed_at')})")
        return True

    print("=" * 64)
    print(f"[ERRORS] *** 선언 대조 실패 [{name}] ***")
    if undeclared:
        print("[ERRORS] 선언에 없는 DIFF가 나타났습니다 — 회계사 판정이 필요합니다:")
        for k in undeclared:
            print(f"[ERRORS]   {k}  {found[k]}")
    if stale:
        print("[ERRORS] 선언 항목이 더 이상 발화하지 않습니다 "
              "(오탐을 고쳤다면 ERRORS.json에서 그 항목을 지우십시오):")
        for k in stale:
            print(f"[ERRORS]   {k}  {real.get(k) or fp.get(k)}")
    if l2_undeclared:
        print("[ERRORS] 선언에 없는 L2 대사 쌍이 나타났습니다:")
        for k in l2_undeclared:
            print(f"[ERRORS]   {k}")
    if l2_stale:
        print("[ERRORS] 선언된 L2 대사 쌍이 발화하지 않습니다:")
        for k in l2_stale:
            print(f"[ERRORS]   {k}")
    print("[ERRORS] ERRORS.json은 도구가 갱신하지 않습니다 — 회계사가 직접 편집하십시오.")
    print("=" * 64)
    return False
