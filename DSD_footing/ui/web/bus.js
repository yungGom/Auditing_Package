// bus.js — sidebar.js ↔ viewer.js를 잇는 최소 이벤트 버스. 그 이상 아무 로직도
// 없다(설계안_UI셸_U3.md §1 승인, 2026-08-27). 두 모듈이 서로를 import하지 않고
// 이 파일 하나만 봐서, U-4의 역방향 연결(지면 클릭 → 목록 선택)도 순환 참조 없이
// 같은 이벤트("selectMark" 계열)로 붙는다.
const listeners = new Map();

export function on(event, fn) {
  if (!listeners.has(event)) listeners.set(event, []);
  listeners.get(event).push(fn);
}

export function emit(event, payload) {
  (listeners.get(event) || []).forEach((fn) => fn(payload));
}
