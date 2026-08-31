# -*- coding: utf-8 -*-
"""api — PyWebView JS 브리지. get_pdf()/get_marks() 두 개만 노출한다.

읽는 파일은 app.py 실행 시 넘겨받은 경로로 고정한다 — JS 쪽에 임의 경로를
읽을 수 있는 API를 열어주지 않는다(설계안_UI셸_U1.md §2). 완전 오프라인:
이 호출은 HTTP가 아니라 웹뷰 엔진의 네이티브 브리지(Windows/WebView2)를 타므로
개발자도구 Network 탭에 잡히지 않는다(설계안 §1 안 1).
"""
import base64
import datetime
import json
import os
import shutil
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import webview  # noqa: E402 — 파일 대화상자(pick_report)에만 쓴다
from marks import sha256_of  # noqa: E402 — 판단 파일 보호(§3)에 재사용, 새 해시 코드 안 만든다
from pypdf import PdfReader  # noqa: E402 — 예상 소요 계산용 페이지 수만 읽는다(분석 아님)

CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# 5축 실측(2026-08-29, foot.py --quiet 분석 소요/페이지수): 0.17~0.41초/페이지.
# 표 밀도에 따라 편차가 크다 — 조선내화 연차(76p, 26.86s)가 삼성(120p, 20.34s)보다
# 오래 걸렸다. 페이지 수만으로는 못 잰다. 그래서 점 추정이 아니라 범위로 보여준다
# (설계안_run_시작화면.md §2 B안, 여유를 둔 0.15~0.45).
_ETA_LOW_S_PER_PAGE = 0.15
_ETA_HIGH_S_PER_PAGE = 0.45


def _paths_for_report(pdf_path):
    """원본 보고서 PDF 경로 → foot.py 명명 규칙 그대로의 산출물 경로 3종.
    final.py의 _base/OUT_PDF 계산과 동일하다(같은 폴더, 확장자만 바꿈)."""
    base = os.path.splitext(pdf_path)[0]
    return {"tick": base + "_틱마크.pdf", "marks": base + "_marks.json",
            "review": base + "_판단.json", "xlsx": base + "_예외색인.xlsx"}


def _atomic_write(path, text):
    """임시 파일에 쓰고 os.replace로 교체한다. 같은 파일에 직접 쓰면 쓰는 도중 앱이
    죽었을 때 반쯤 쓰인 JSON이 남아 **판단을 전부 잃는다**(U-6 승인 조건)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class Api:
    def __init__(self, pdf_path=None, marks_path=None, review_path=None):
        self._pdf_path = pdf_path
        self._marks_path = marks_path
        self._review_path = review_path
        self._doc = None            # marks.json 원문 캐시 (읽기 전용)
        self._judgments = {}        # 메모리 사본 — 파일이 원본이다
        self._window = None         # bind_window()로 app.py가 넘겨준다 — 화면 전환·진행 push에 씀
        self._analyzing = False
        self._analysis_proc = None  # 진행 중인 foot.py subprocess (창 닫힘 시 종료 대상)
        self._analysis_paths = None # 진행 중인 분석의 산출물 경로(중단 시 부분 파일 정리용)
        self._startup_arg = None    # app.py가 CLI 인자로 받은 원본 PDF — start.js가 한 번만 꺼내간다

    def get_startup_arg(self):
        """CLI 인자(python ui/app.py <원본.pdf>)로 받은 경로. 대화상자로 고른 경로와
        완전히 같은 흐름(openPath)을 태우기 위해 JS가 시작 시 한 번 물어본다 —
        Python이 직접 begin_open을 부르면 경고 대화상자 같은 UI가 안 뜬 채로
        진행될 위험이 있다(app.py 모듈 docstring 참고)."""
        arg, self._startup_arg = self._startup_arg, None  # 한 번만 반환
        return {"path": arg}

    def bind_window(self, window):
        """app.py가 webview.create_window() 직후 부른다. load_url·evaluate_js로
        시작 화면 → 검토 화면 전환, 분석 진행 상태 push에 쓴다."""
        self._window = window

    def get_pdf(self):
        """→ {name, base64} 고정 파일 하나. 실패 시 {error: 사유}(조용히 빈 값 금지)."""
        if not self._pdf_path:
            return {"error": "열린 보고서가 없습니다."}
        try:
            with open(self._pdf_path, "rb") as f:
                data = f.read()
        except OSError as e:
            return {"error": f"파일을 열 수 없습니다: {e}"}
        return {"name": os.path.basename(self._pdf_path),
                "base64": base64.b64encode(data).decode("ascii")}

    def get_marks(self):
        """→ {marks, counts}. annotations[]는 여기서부터 걸러 JS로 아예 보내지 않는다 —
        U-2 요구("annotations는 목록에 넣지 않는다")를 렌더 단계가 아니라 전송 단계에서
        지킨다(가장 강한 보장: 브라우저 메모리에 annotations가 존재조차 하지 않음).
        marks.json이 없으면(구형 산출물, 또는 foot.py 밖에서 만든 PDF) {error: 사유}."""
        if not self._marks_path:
            return {"error": "이 PDF는 foot.py 산출물이 아닙니다(파일명이 _틱마크.pdf로 끝나지 않음)."}
        try:
            with open(self._marks_path, encoding="utf-8") as f:
                doc = json.load(f)
        except OSError as e:
            return {"error": f"marks.json을 열 수 없습니다: {e}"}
        except json.JSONDecodeError as e:
            return {"error": f"marks.json 형식이 올바르지 않습니다: {e}"}
        self._doc = doc
        res = {"marks": doc.get("marks", []),
               "counts": doc.get("document", {}).get("counts", {})}
        # 저장된 판단을 얹어 보낸다. 실패는 조용히 넘기지 않는다 — 판단이 사라진 것처럼
        # 보이면 회계사가 다시 검토하게 되고, 그건 조서 신뢰의 문제다.
        rv = self._load_review(doc)
        if rv.get("error"):
            res["review_error"] = rv["error"]
        else:
            self._judgments = rv.get("judgments", {})
            applied, missing = 0, []
            ids = {m["id"] for m in res["marks"]}
            for mid, j in self._judgments.items():
                if mid not in ids:
                    missing.append(mid); continue
                applied += 1
            for m in res["marks"]:
                j = self._judgments.get(m["id"])
                if j:
                    m["status"] = j.get("status", m.get("status"))
                    m["comment"] = j.get("comment")
                    m["reviewed_at"] = j.get("reviewed_at")
                    m["reviewed_by"] = j.get("reviewed_by")
            res["review"] = {"applied": applied, "missing": missing,
                             "reviewer": rv.get("reviewer") or ""}
        return res

    # ── 판단 파일 ────────────────────────────────────────────────────
    def _load_review(self, doc):
        """판단 파일을 읽는다. 원본 PDF가 다르면 **적용하지 않고 멈춘다** —
        무시하고 열면 회계사가 '판단이 사라졌다'고 오해한다(U-6 승인 조건)."""
        if not self._review_path or not os.path.isfile(self._review_path):
            return {"judgments": {}}
        try:
            with open(self._review_path, encoding="utf-8") as f:
                rv = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            return {"error": f"판단 파일을 읽을 수 없습니다: {e}"}
        want = (doc.get("source") or {}).get("sha256")
        got = rv.get("source_sha256")
        if want and got and want != got:
            return {"error": ("판단 파일이 다른 PDF의 것입니다 — 적용하지 않았습니다.\n"
                              f"판단 파일이 기록한 원본: {rv.get('source_pdf') or '(파일명 없음)'}\n"
                              f"지금 연 PDF: {(doc.get('source') or {}).get('pdf') or '(알 수 없음)'}\n"
                              f"파일 경로: {self._review_path}")}
        return rv

    def save_judgment(self, mark_id, status, comment=None):
        """판단 1건을 즉시 파일에 쓴다. 쓰는 대상은 판단 파일뿐 — marks.json·PDF에는
        절대 쓰지 않는다(분석 산출물은 UI가 손대지 않는다는 U-1 이래의 경계)."""
        if not self._review_path:
            return {"error": "판단을 저장할 경로가 없습니다."}
        if self._doc is None:
            return {"error": "marks.json을 아직 읽지 않았습니다."}
        self._judgments[mark_id] = {
            "status": status,
            "comment": (comment or "").strip() or None,
            "reviewed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "reviewed_by": self.get_reviewer().get("reviewer") or None,
        }
        src = self._doc.get("source") or {}
        payload = {
            "schema": "dsd-footing-review/1",
            "source_pdf": src.get("pdf"),
            "source_sha256": src.get("sha256"),
            "marks_run": (self._doc.get("run") or {}).get("run_ts"),
            "reviewer": self.get_reviewer().get("reviewer") or "",
            "saved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "judgments": self._judgments,
        }
        try:
            _atomic_write(self._review_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        except OSError as e:
            return {"error": f"판단을 저장하지 못했습니다: {e}"}
        return {"ok": True, "saved": len(self._judgments), "path": self._review_path}

    # ── 검토자 · 개발자 모드 ────────────────────────────────────────────
    def _load_config(self):
        try:
            with open(CONFIG, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def get_reviewer(self):
        """ui/config.json에 이름 하나만 둔다. 인증이 아니라 '누가 검토했는지'다.
        이 파일은 .gitignore 대상 — 사람 이름이 저장소에 들어가면 안 된다."""
        return {"reviewer": str(self._load_config().get("reviewer") or "").strip()}

    def set_reviewer(self, name):
        name = (name or "").strip()
        if not name:
            return {"error": "이름을 입력하십시오."}
        cfg = self._load_config()          # 병합해서 쓴다 — dev_mode 등 다른 설정을 지우지 않는다
        cfg["reviewer"] = name
        try:
            _atomic_write(CONFIG, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
        except OSError as e:
            return {"error": f"설정을 저장하지 못했습니다: {e}"}
        return {"ok": True, "reviewer": name}

    def get_dev_mode(self):
        """ERRORS.json 선언 조각 버튼 노출 여부. 기본값 false — config.json이 없거나
        키가 없으면 일반 회계사 화면에는 개발 전용 기능이 안 보여야 한다(2026-08-29
        승인). ERRORS.json은 도구의 회귀 기준이고 관리자는 개발자이지, 자기 감사보고서를
        풋팅하는 회계사가 아니다. 값은 사람이 config.json을 직접 편집해 켠다 — UI에
        토글을 두지 않는다(실수로 켜지는 경로를 만들지 않기 위함)."""
        return {"dev_mode": bool(self._load_config().get("dev_mode") is True)}

    # ── 시작 화면 — 보고서 열기 · 최근 목록 · 분석 진행 ────────────────────
    def get_tool_version(self):
        """final.py의 VER 계산과 같은 패턴(git 짧은 커밋 해시). 시작 화면 표시용."""
        try:
            r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                               capture_output=True, text=True, cwd=ROOT)
            return {"version": r.stdout.strip() or "nogit"}
        except Exception:
            return {"version": "nogit"}

    def list_recents(self):
        """최근 연 보고서. 경로가 사라진 항목도 지우지 않고 exists=False로 낸다 —
        화면이 회색 처리하고, 클릭 시 확인 후 remove_recent를 부른다(설계안 §6).
        조용히 전부 지우면 '연 적이 있었다'는 사실 자체를 잃는다."""
        cfg = self._load_config()
        out = []
        for r in cfg.get("recents", []):
            p = r.get("path") or ""
            out.append({"path": p, "name": r.get("name") or os.path.basename(p),
                        "last_opened": r.get("last_opened") or "", "exists": os.path.isfile(p)})
        return {"recents": out}

    def remove_recent(self, path):
        cfg = self._load_config()
        cfg["recents"] = [r for r in cfg.get("recents", []) if r.get("path") != path]
        try:
            _atomic_write(CONFIG, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
        except OSError as e:
            return {"error": str(e)}
        return {"ok": True}

    def _touch_recent(self, tick_path):
        """표시 이름은 원본 보고서 이름이다(_틱마크.pdf가 아니다) — 회계사는 원본
        파일명으로 문서를 기억한다. 저장 실패는 조용히 넘어간다 — 최근 목록은
        편의 기능이라 판단 파일과 달리 실패가 치명적이지 않다."""
        base = tick_path[:-len("_틱마크.pdf")] if tick_path.endswith("_틱마크.pdf") \
            else os.path.splitext(tick_path)[0]
        name = os.path.basename(base) + ".pdf"
        cfg = self._load_config()
        recents = [r for r in cfg.get("recents", []) if r.get("path") != tick_path]
        recents.insert(0, {"path": tick_path, "name": name,
                           "last_opened": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
        cfg["recents"] = recents[:10]
        try:
            _atomic_write(CONFIG, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
        except OSError:
            pass

    def pick_report(self):
        """OS 파일 선택 대화상자(WinForms OpenFileDialog, 로컬 API — 오프라인 무관,
        설계안 §8 실측 확인). 취소는 오류가 아니다 — {"path": None}으로 구분한다."""
        if not self._window:
            return {"error": "창이 준비되지 않았습니다."}
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG, file_types=("PDF 파일 (*.pdf)", "모든 파일 (*.*)"))
        return {"path": (result[0] if result else None)}

    def begin_open(self, path):
        """시작 화면(대화상자·최근 목록 공통)의 단일 진입점 — 설계안 §3~4 흐름 전체.
        반환: {status:"opened"} 즉시 전환 / {status:"analyzing", eta} 분석 시작 /
              {status:"warn_reanalyze", message} 판단 파일 보호로 진행 중단(확인 필요) /
              {error} 실패."""
        if not path or not os.path.isfile(path):
            return {"error": f"파일을 찾을 수 없습니다: {path}"}
        if path.endswith("_틱마크.pdf"):
            return self._open_tick_directly(path)  # 이미 만든 산출물 직접 열기(분석 없음)

        paths = _paths_for_report(path)
        try:
            cur_sha = sha256_of(path)
        except OSError as e:
            return {"error": f"파일을 읽을 수 없습니다: {e}"}

        # §4 — 이미 분석됨: marks.json이 있고 지금 고른 파일과 내용이 같으면 생략
        if os.path.isfile(paths["marks"]):
            try:
                with open(paths["marks"], encoding="utf-8") as f:
                    existing = json.load(f)
                if (existing.get("source") or {}).get("sha256") == cur_sha:
                    return self._open_tick_directly(paths["tick"])
            except (OSError, json.JSONDecodeError):
                pass  # 손상된 marks.json — 재분석으로 흘러간다

        # §3 — 판단 파일 보호: 기존 판단이 있는데 지금 파일과 내용이 다르면 진행 전에 묻는다.
        # 내용이 같으면(R-1 결정론상 재분석해도 같은 marks.json이 나옴) 그냥 진행한다.
        if os.path.isfile(paths["review"]):
            try:
                with open(paths["review"], encoding="utf-8") as f:
                    old_sha = json.load(f).get("source_sha256")
            except (OSError, json.JSONDecodeError):
                old_sha = None
            if old_sha and old_sha != cur_sha:
                return {"status": "warn_reanalyze", "path": path,
                        "message": ("이 보고서에 대한 기존 판단 기록이 있습니다만, 지금 선택한 "
                                   "파일과 내용이 다릅니다(원본이 바뀐 것으로 보입니다).\n\n"
                                   "재분석해도 기존 판단 파일 자체는 지워지지 않지만, 새 분석 "
                                   "결과와는 내용이 달라 자동으로 적용되지 않습니다.\n\n"
                                   f"기존 판단 파일: {paths['review']}")}

        return self._start_analysis(path, paths)

    def confirm_reanalyze(self, path):
        """경고 대화상자에서 [계속 진행]을 눌렀을 때. 기존 판단 파일을 타임스탬프
        백업으로 복사한 뒤(보험용) 분석을 시작한다."""
        paths = _paths_for_report(path)
        if os.path.isfile(paths["review"]):
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            try:
                shutil.copy2(paths["review"], f"{paths['review']}.bak-{ts}")
            except OSError as e:
                return {"error": f"기존 판단 파일을 백업하지 못했습니다: {e} — 진행을 중단합니다."}
        return self._start_analysis(path, paths)

    def _open_tick_directly(self, tick_path):
        if not os.path.isfile(tick_path):
            return {"error": f"파일을 찾을 수 없습니다: {tick_path}"}
        base = tick_path[:-len("_틱마크.pdf")]
        self._pdf_path = tick_path
        marks_path = base + "_marks.json"
        self._marks_path = marks_path if os.path.isfile(marks_path) else None
        self._review_path = base + "_판단.json"
        self._doc = None; self._judgments = {}
        self._touch_recent(tick_path)
        self._goto_viewer()
        return {"status": "opened"}

    def _start_analysis(self, path, paths):
        if self._analyzing:
            return {"error": "이미 분석이 진행 중입니다."}
        try:
            npages = len(PdfReader(path).pages)
        except Exception:
            npages = None
        self._analyzing = True
        self._analysis_paths = paths
        threading.Thread(target=self._run_analysis, args=(path, paths), daemon=True).start()
        eta = None
        if npages:
            eta = {"pages": npages, "low_s": round(npages * _ETA_LOW_S_PER_PAGE),
                  "high_s": round(npages * _ETA_HIGH_S_PER_PAGE)}
        return {"status": "analyzing", "eta": eta}

    def _run_analysis(self, path, paths):
        """백그라운드 스레드 — foot.py를 subprocess로 돌리고 경과 시간을 push한다.
        정확한 페이지 진행률(final.py 훅)은 이번 범위 밖이다(설계안 §2, B안).
        판정 파이프라인은 여기서 읽기만 한다 — foot.py를 그대로 부를 뿐 로직을
        재구현하지 않는다.

        ★ stderr는 PIPE가 아니라 파일로 받는다. PIPE로 잡고 자식이 끝날 때까지
        안 읽으면, pdfplumber의 CropBox 경고 등이 쌓여 OS 파이프 버퍼(보통 64KB)를
        채우는 순간 자식이 write()에서 멈추고 부모는 poll()만 반복해 **영원히 안
        끝나는 교착 상태**가 된다(음성 테스트로 재현·확인, 36페이지 문서에서도
        발생). 파일은 그런 크기 제한이 없어 이 문제 자체가 없다."""
        start = time.time()
        log_path = paths["marks"] + ".analysis.log"
        try:
            with open(log_path, "w", encoding="utf-8") as logf:
                proc = subprocess.Popen(
                    [sys.executable, "-u", os.path.join(ROOT, "foot.py"), path, "--quiet"],
                    cwd=ROOT, stdout=subprocess.DEVNULL, stderr=logf, text=True)
                self._analysis_proc = proc
                while proc.poll() is None:
                    time.sleep(0.5)
                    self._push_progress({"elapsed": round(time.time() - start)})
            if proc.returncode != 0:
                tail = ""
                try:
                    with open(log_path, encoding="utf-8", errors="replace") as f:
                        tail = f.read()[-800:]
                except OSError:
                    pass
                self._push_progress({"error": f"분석이 실패했습니다(종료코드 {proc.returncode}).\n{tail}"})
                return
        except Exception as e:
            self._push_progress({"error": f"분석을 시작하지 못했습니다: {type(e).__name__}: {e}"})
            return
        finally:
            self._analyzing = False
            self._analysis_proc = None
            self._analysis_paths = None
            try: os.remove(log_path)
            except OSError: pass

        if not os.path.isfile(paths["tick"]):
            self._push_progress({"error": "분석이 끝났지만 산출물을 찾을 수 없습니다."})
            return
        self._pdf_path = paths["tick"]
        self._marks_path = paths["marks"] if os.path.isfile(paths["marks"]) else None
        self._review_path = paths["review"]
        self._doc = None; self._judgments = {}
        self._touch_recent(paths["tick"])
        self._goto_viewer()

    def cancel_analysis(self):
        """분석 중 창이 닫힐 때 app.py의 closing 핸들러가 부른다(설계안 §5).
        subprocess를 종료한다 — 페이지 루프(대부분의 시간) 도중이면 애초에 파일이
        없어 정리할 게 없다. marks.json 쓰기 도중(아주 짧은 구간)에 걸려 잘린
        파일이 남았을 수 있으니 지운다. **_판단.json은 손대지 않는다** — foot.py가
        그 파일의 존재를 아예 모르므로 여기서도 건드릴 이유가 없다."""
        if self._analysis_proc:
            try:
                self._analysis_proc.terminate()
            except Exception:
                pass
        if self._analysis_paths:
            mj = self._analysis_paths.get("marks")
            if mj and os.path.isfile(mj):
                try:
                    json.load(open(mj, encoding="utf-8"))  # 온전하면 그대로 둔다(드묾)
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    try: os.remove(mj)
                    except OSError: pass
        self._analyzing = False

    def _push_progress(self, payload):
        if not self._window:
            return
        try:
            self._window.evaluate_js(
                f"window.__dsdProgress && window.__dsdProgress({json.dumps(payload, ensure_ascii=False)})")
        except Exception:
            pass  # 창이 이미 닫혔을 수 있다 — 무시(cancel_analysis가 별도로 정리한다)

    def _goto_viewer(self):
        if not self._window:
            return
        index_html = os.path.join(HERE, "web", "index.html")
        self._window.load_url("file:///" + index_html.replace(os.sep, "/"))

    # ── 최종 출력 ────────────────────────────────────────────────────
    def export_final(self):
        """판단을 반영한 <원본>_검토완료.pdf. 원본 marks.json은 읽기만 하고,
        status를 반영한 **사본**을 render_all에 넘긴다."""
        import copy, render, summary
        if self._doc is None:
            return {"error": "marks.json을 아직 읽지 않았습니다."}
        base = self._pdf_path[:-len("_틱마크.pdf")] if self._pdf_path.endswith("_틱마크.pdf") \
            else os.path.splitext(self._pdf_path)[0]
        src_pdf = base + ".pdf"
        if not os.path.isfile(src_pdf):
            return {"error": f"원본 PDF를 찾을 수 없습니다: {src_pdf}"}
        out = base + "_검토완료.pdf"
        try:
            doc = copy.deepcopy(self._doc)
            for m in doc.get("marks", []):
                j = self._judgments.get(m["id"])
                if j: m["status"] = j.get("status", m.get("status"))
            tick = base + "_틱마크.pdf"
            render.render_all(src_pdf, doc, tick + ".tmp_final", quiet=True)
            t = summary.append_to(tick + ".tmp_final", doc, self._judgments,
                                  self.get_reviewer().get("reviewer"), out)
            os.remove(tick + ".tmp_final")
        except Exception as e:
            return {"error": f"출력에 실패했습니다: {type(e).__name__}: {e}"}
        return {"ok": True, "path": out, "pending": t["pending"],
                "approved": t["approved"], "removed": t["removed"], "total": t["total"]}

    def export_errors_snippet(self):
        """'차이 아님'으로 판정한 항목을 ERRORS.json 형식 문자열로 만든다.
        ★ 자동 반영이 아니라 복사 편의다. task를 비워 내보내므로 그대로 붙여넣으면
        C안 로더가 'task 없음'으로 거부한다 — 복사만으로는 선언이 성립하지 않는다."""
        if self._doc is None:
            return {"error": "marks.json을 아직 읽지 않았습니다."}
        import errors as errmod
        out = []
        for m in self._doc.get("marks", []):
            j = self._judgments.get(m["id"]) or {}
            if j.get("status") != "removed" or m.get("level") == "L2":
                continue
            ev = m.get("evidence") or {}
            if ev.get("disp") is None or ev.get("diff") is None:
                continue
            out.append({
                "key": errmod.l1_key(m["page"], (m.get("source") or {}).get("check"),
                                     ev["disp"], ev["diff"]),
                "account": m.get("account") or "",
                "reason": j.get("comment") or "",
                "task": "",
            })
        return {"ok": True, "count": len(out),
                "text": json.dumps(out, ensure_ascii=False, indent=2)}

    def get_glyph_offsets(self):
        """→ ui/glyph_offsets.json 내용. UI 히트영역의 **유일한 출처**다 —
        값을 JS에 복제하지 않는 이유와 게이트(glyph_gate.py)는 그 파일 주석 참고."""
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glyph_offsets.json")
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            return {"error": f"glyph_offsets.json을 읽을 수 없습니다: {e}"}
