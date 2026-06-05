import { useEffect } from "react";
import { SHAPES } from "../shapes";

/**
 * 단축키 안내 모달 — Topbar 의 ? 버튼 또는 키보드 `?` 로 열린다.
 * Esc 또는 배경 클릭으로 닫힘.
 */
export function ShortcutHelpModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  // 배경 스크롤 잠금 + Esc 닫기는 useShortcuts 가 ?·Esc 를 같이 처리하므로 여기선 생략.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const shapeShortcuts = SHAPES.filter((s) => !!s.shortcut);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-lg border border-slate-200 bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900">단축키 안내</h2>
            <p className="text-[11px] text-slate-500">
              도형 단축키는 입력 필드 안에서 동작하지 않습니다.
              Ctrl+Z / Ctrl+Y 는 어디서든 작동.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            aria-label="닫기"
          >
            ✕
          </button>
        </header>

        <div className="grid grid-cols-1 gap-6 p-5 sm:grid-cols-2">
          <Section title="도형 추가">
            <Hint>
              ① 키만 누르고 떼기 → 캔버스 중앙에 1개 추가
              <br />② 키를 누른 채 캔버스 클릭 → 그 자리에 추가 (연속 가능)
            </Hint>
            <Table>
              {shapeShortcuts.map((s) => (
                <Row key={s.key} k={s.shortcut!} label={s.label} />
              ))}
            </Table>
          </Section>

          <Section title="선택 / 편집">
            <Table>
              <Row k="클릭" label="노드·엣지 선택" />
              <Row k="Ctrl+클릭" label="추가 선택 (다중)" />
              <Row k="박스 드래그" label="영역 선택 (일부 걸쳐도 선택)" />
              <Row k="Ctrl+A" label="전체 선택" />
              <Row k="Del / ⌫" label="선택 노드·엣지 삭제" />
              <Row k="Ctrl+C" label="선택 노드·엣지 복사" />
              <Row k="Ctrl+V" label="붙여넣기 (+40px 오프셋)" />
              <Row k="Ctrl+D" label="복제 (복사+붙여넣기 한 번에)" />
              <Row k="L" label="선택 노드 위치 고정/해제 🔒 (선택 없으면 Link 추가)" />
              <Row k="Ctrl+Z" label="실행 취소 (Undo)" />
              <Row k="Ctrl+Y" label="다시 실행 (Redo)" />
              <Row k="Ctrl+Shift+Z" label="다시 실행 (Redo, Mac 관례)" />
              <Row k="Esc" label="추가 대기 취소 / 도움말 닫기" />
            </Table>

            <Section title="화면" tight>
              <Table>
                <Row k="마우스 휠" label="줌 인 / 아웃" />
                <Row k="Space + 드래그" label="캔버스 이동 (패닝)" />
                <Row k="?" label="이 도움말 열기 / 닫기" />
              </Table>
            </Section>
          </Section>
        </div>

        <footer className="border-t border-slate-200 bg-slate-50 px-5 py-2 text-[11px] text-slate-500">
          Undo 기록은 약 50단계 보관. 빠르게 연속된 변경(드래그·연속 타이핑)은
          한 단계로 묶입니다.
        </footer>
      </div>
    </div>
  );
}

function Section({
  title,
  tight,
  children,
}: {
  title: string;
  tight?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={tight ? "mt-3" : "space-y-2"}>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </div>
      {children}
    </div>
  );
}

function Table({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-col gap-1">{children}</div>;
}

function Row({ k, label }: { k: string; label: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded px-1 py-0.5 text-xs hover:bg-slate-50">
      <span className="text-slate-700">{label}</span>
      <kbd className="rounded border border-slate-300 bg-white px-1.5 py-0.5 font-mono text-[10px] font-semibold text-slate-600">
        {k}
      </kbd>
    </div>
  );
}

function Hint({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded border border-slate-200 bg-slate-50 p-2 text-[11px] leading-snug text-slate-600">
      {children}
    </p>
  );
}
