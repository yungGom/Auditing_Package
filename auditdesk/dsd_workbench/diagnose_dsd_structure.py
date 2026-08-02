# -*- coding: utf-8 -*-
"""검토 입력단 진단 — DSD 구조 통계 (부록 D-1, 사용자 로컬 실행용).

용도: 검토 대상 DSD가 '왜 시트가 이렇게 갈라졌는가'를 로컬에서
진단한다. 코어 수정 없음 — 읽기 전용.

실행:  python diagnose_dsd_structure.py <파일.dsd>

출력은 **구조 통계만**: 절(節) 노드 수·텍스트 분량, 'N. 제목' 패턴
주석 개수, FS 제목 인식 결과 개수. 계정명·수치·문장은 일절 출력하지
않는다 (반출 안전 설계 — 결과 화면을 그대로 공유해도 안전).

판정 기준:
  ① 절 수 ≈ 생성 시트 수 이고 텍스트 주석 수 ≫ 절 수
     → "원본 뭉텅이 작성" (도구 정상 — 작성자가 목차 구조 없이 큰
        절에 몰아쓴 문서. B-6/B-6-mini 텍스트 분할 영역)
  ② 절 수 > 시트 수
     → "스캐너 미인식" (도구 버그 — 이 출력 화면이 곧 재현 정보,
        핫픽스 대상으로 전달)
"""
import io
import re
import sys
import zipfile


def main(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        has_meta = any(n.lower() == "meta.xml" for n in names)
        entry = next((n for n in names
                      if n.lower() in ("contents.xml", "content.xml")),
                     None) or next(n for n in names
                                   if n.lower().endswith(".xml"))
        text = z.read(entry).decode("utf-8", "ignore")
        kind = "zip(DSD)"
    except zipfile.BadZipFile:
        text = data.decode("utf-8", "ignore")
        has_meta, kind = False, "평문 XML"

    print("=== DSD 구조 진단 (통계만 — 내용 미출력) ===")
    print(f"컨테이너: {kind} · meta.xml {'있음(편집기 계열)' if has_meta else '없음(수신물/래핑)'}")

    # ⓐ 문서 트리 절(節) 노드 — SECTION-1/-2 + TITLE 개수·텍스트 분량
    sec = []
    for m in re.finditer(r"<SECTION-(\d)[^>]*>", text):
        end = text.find(f"</SECTION-{m.group(1)}>", m.end())
        sec.append((int(m.group(1)), m.start(),
                    (end - m.start()) if end > 0 else 0))
    n_titles = len(re.findall(r"<TITLE[^>]*>", text))
    print(f"ⓐ 절 노드: SECTION-1 {sum(1 for l, _, _ in sec if l == 1)}개"
          f" · SECTION-2 {sum(1 for l, _, _ in sec if l == 2)}개"
          f" · TITLE {n_titles}개")
    for i, (lv, _pos, size) in enumerate(sec, 1):
        print(f"   절{i} (SECTION-{lv}): 텍스트 {size:,}자")

    # ⓑ 텍스트 'N. 제목' 패턴 주석 개수 (표 내부 제외 근사 — P/SPAN 계열)
    txt_notes = set()
    for m in re.finditer(
            r"(?:<P[^>]*>|<SPAN[^>]*>)\s*(\d{1,2})\s*[.．]\s*[가-힣]",
            text):
        txt_notes.add(int(m.group(1)))
    print(f"ⓑ 텍스트 'N. 제목' 패턴 주석: {len(txt_notes)}개"
          f" (번호 범위 {min(txt_notes)}~{max(txt_notes)})"
          if txt_notes else "ⓑ 텍스트 주석 패턴: 0개")

    # ⓒ FS 제목 인식 결과 (dsd_tool 스캐너 — 개수·시트명만)
    try:
        sys.path.insert(0, __file__.rsplit("\\", 1)[0]
                        if "\\" in __file__ else ".")
        from dsd_tool.scanner import scan
        doc = scan(text)
        fs = [b.sheet_name for b in doc.fs_blocks]
        print(f"ⓒ FS 제목 인식: {len(fs)}개 {fs}")
        print(f"   주석 시트(마크업 경계 분할): {len(doc.notes)}개"
              f" · 탈락 FS 제목: {len(doc.fs_dropped or [])}개"
              f" · 미분류 FS유사 제목: {len(doc.fs_unclassified or [])}개")
        n_sheets = len(doc.notes)
        n_sec2 = sum(1 for l, _, _ in sec if l == 2)
        print()
        if n_sec2 > n_sheets + len(fs):
            print("판정: ② 절 수 > 시트 수 — 스캐너 미인식 의심 (버그)."
                  " 이 출력 화면을 재현 정보로 전달하세요.")
        elif txt_notes and len(txt_notes) > max(n_sheets, 1) * 2:
            print("판정: ① 원본 뭉텅이 작성 — 도구 정상, 작성자 목차"
                  " 구조 부재. 텍스트 2차 분할(B-6 계열) 영역.")
        else:
            print("판정: 구조 정상 범위 — 시트 분할이 문서 구조와 일치.")
    except Exception as e:
        print(f"ⓒ 스캐너 인식 생략 (dsd_tool 미탑재 환경): {type(e).__name__}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python diagnose_dsd_structure.py <파일.dsd>")
        sys.exit(1)
    main(sys.argv[1])
