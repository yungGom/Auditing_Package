"""F-3: 승계 모드 — 자기 기말 XBRL 자산으로 분반기 워크시트 생성.

원칙 (스펙 F-3):
1. 자기 기말 인스턴스의 element 선택·확장 정의·role 구성을 그대로 승계
2. D-3b 추천은 기말에 없던 신규 계정에만 작동 (판단 최소화)
3. 기간 체계만 분반기로 변환 (F-1의 PERIOD_LABELS 규칙 재사용)
4. D-4c 연동: 승계 전 신버전 택사노미 호환성 — 폐지(노랑) element는
   승계 대신 경고 + D-3b 대체 후보 병기

입력: dart_explorer export_succession_assets가 산출한 JSON
(파일 교환 경계 — dsd_workbench는 네트워크·인스턴스 직접 수신 금지).
"""
import json
import os
import re

from .mapping import normalize

# DSD 본문·주석 라벨의 목차 접두 ('1.', 'Ⅰ.', '(1)', '가.') — 인스턴스
# 라벨에는 없는 장식이라 승계 조회 전에 벗긴다
_NUMBERING_RE = re.compile(
    r"^\s*(?:\(?[0-9]+\)?|[IVXLCivxlcⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅰ-ⅹ]+|[가-힣]\))\s*[.)]\s*")


def _clean(label):
    s = str(label)
    prev = None
    while prev != s:
        prev = s
        s = _NUMBERING_RE.sub("", s)
    return normalize(s)


class SuccessionAssets:
    """자기 기말 승계 자산 (읽기 전용 스냅샷)."""

    def __init__(self, json_path):
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        self.source = data.get("source", "")
        self.against = data.get("against")
        self.roles = data.get("roles", [])
        self.taxcheck = data.get("taxcheck", {})

        # 라벨 → element 목록 (팩트 수 내림차순 — 동라벨 복수 시 다빈도 우선)
        self.by_label = {}
        self.element_ids = set()
        for e in sorted(data.get("elements", []),
                        key=lambda x: -(x.get("n_facts") or 0)):
            eid = e["element_id"]
            if eid.startswith("dart-gcd"):
                continue
            self.element_ids.add(eid)
            qn = _clean(e.get("label_ko") or "")
            if len(qn) >= 2:
                self.by_label.setdefault(qn, []).append(e)

        self.member_by_label = {}
        for m in data.get("members", []):
            qn = _clean(m.get("label_ko") or "")
            if qn:
                self.member_by_label.setdefault(qn, m)

    def inherit(self, label, min_sim=0.55):
        """계정 라벨 → 기말 사용 element (없으면 None = 신규 계정).

        1차 정확 일치, 2차 유사도 폴백 — 폴백도 자기 기말 사용 element
        풀에 한정한다 (판단 최소화 원칙 유지). 실측 근거: 인스턴스가
        표준 라벨을 그대로 쓰면 DSD 표기와 어긋남 ('재고자산' ↔
        '유동재고자산', '자산총계' ↔ '자산').
        """
        from .mapping import similarity
        qn = _clean(label)
        hits = self.by_label.get(qn)
        if hits:
            return dict(hits[0], sim=1.0)
        if not qn:
            return None
        raw = str(label)
        best = None
        for key, els in self.by_label.items():
            s = similarity(qn, raw, els[0].get("label_ko") or "")
            if qn in key or key in qn:          # 포함관계 보정
                ratio = min(len(qn), len(key)) / max(len(qn), len(key))
                s = max(s, 0.6 + 0.4 * ratio)
            if s >= min_sim and (best is None or s > best[1]):
                best = (els[0], s)
        return dict(best[0], sim=round(best[1], 2)) if best else None

    def inherit_member(self, label):
        """행 라벨 → 기말 문맥에서 사용된 member (없으면 None)."""
        return self.member_by_label.get(_clean(label))

    def taxcheck_of(self, element_id):
        """D-4c 상태 {status, detail} — 미점검이면 None."""
        return self.taxcheck.get(element_id)

    def find_role(self, note_title):
        """주석 제목 → 자기 기말 role 승계 (번호 우선, 제목 폴백).

        자사 pre.xml 정의는 '[D822105] 10. 유형자산' 형식 — 주석 번호가
        일치하면 결정적 승계.
        """
        import re
        m = re.match(r"^\s*(\d+)\s*\.", str(note_title))
        if m:
            num = m.group(1)
            pat = re.compile(rf"\]\s*{num}\s*\.")
            hits = [r for r in self.roles
                    if r["code"].startswith("D8") and pat.search(
                        r["definition"] or "")]
            if len(hits) == 1:
                return hits[0]
        qn = normalize(str(note_title))
        for r in self.roles:
            if not r["code"].startswith("D8"):
                continue
            import re as _re
            title = _re.sub(r"^\[D\d{6}\]\s*(?:\d+\s*\.\s*)?", "",
                            r["definition"] or "")
            if qn and normalize(title) == qn:
                return r
        return None


def load_assets(json_path):
    if not os.path.exists(json_path):
        raise FileNotFoundError(
            f"승계 자산 JSON 없음: {json_path} — dart_explorer "
            "export_succession_assets(기말 패키지 폴더)로 먼저 산출하세요")
    return SuccessionAssets(json_path)
