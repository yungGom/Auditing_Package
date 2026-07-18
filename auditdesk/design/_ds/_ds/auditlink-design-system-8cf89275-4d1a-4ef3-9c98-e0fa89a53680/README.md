# AuditLink Design System

**AuditLink** (오딧링크) is a Korean-language desktop application for accounting auditors to manage their audit engagements — tracking clients, fiscal years, audit phases (기중/기말), account-level tasks, internal control (ICFR) tests, PBC request items, and deadlines. It is built as a local-first tool: React + Vite frontend wrapped in PyWebView with a FastAPI + SQLite backend, shipped as a Windows EXE.

The product is professional, navy-toned, and information-dense. It aims to give a single overworked auditor (or a small team lead) at-a-glance control over multiple concurrent audit engagements — dashboard progress rings, calendar-driven deadline tracking, keyboard-driven search, and a hierarchical tree navigation (FY → Client → Phase → Account → Task).

---

## Sources used to build this system

- **Codebase**: GitHub `yungGom/Auditing_Package`, branch `main`, path `auditlink/`. Imported at the project root (not under `auditlink/`).
- **Referenced docs in the codebase**: `CLAUDE.md`, `FEATURE_SPEC.md`, `BUGFIX.md`, `TESTING_CHECKLIST.md`.
- **Design tokens**: extracted directly from `tailwind.config.js` (Material-3-ish Navy palette) and `index.html` (Google Fonts imports: Manrope, Inter, Material Symbols Outlined).
- **Iconography**: the codebase uses Google's **Material Symbols Outlined** web font (via Google Fonts CSS). All icon references in code are string glyph names (`dashboard`, `work`, `verified`, etc.).
- **No Figma file was provided.** All visual truth is lifted from `src/components/*.jsx`, `src/pages/*.jsx`, and `tailwind.config.js`.

> Note: the `public/favicon.svg` shipped in the repo is a purple/violet placeholder from a different project and does **not** match AuditLink's brand. AuditLink's actual mark (as used in `Sidebar.jsx`) is the Material Symbols `verified` glyph rendered in brand navy `#001e40`. This design system treats that navy-checkmark-shield as the logo.

---

## Index (what's in this folder)

| Path | What it is |
|---|---|
| `README.md` | This file — brand context, content & visual foundations, iconography. |
| `SKILL.md` | Claude Skill manifest so this system can be dropped into Agent Skills / Claude Code. |
| `colors_and_type.css` | Drop-in CSS variables for all brand colors + type tokens + semantic defaults. |
| `fonts/` | Font-loading CSS (uses Google Fonts — Manrope, Inter, Material Symbols Outlined). |
| `assets/` | Logo mark, favicon, and re-exported source icons from the codebase. |
| `preview/` | Small HTML cards registered to the Design System tab (colors, type, components, etc.). |
| `ui_kits/auditlink-app/` | Working React prototype recreating the desktop app — Sidebar, Header, Dashboard, Engagements, task modals. |

---

## Content Fundamentals

AuditLink is a **professional tool for Korean CPAs**. Copy is in **Korean**, with English technical jargon only where universal (e.g. "FY", "ICFR", "D-Day").

### Voice & tone

- **Formal-neutral professional** (평어 / 직장인체). Not polite honorifics (`-습니다`/`-세요`), not casual. Short, declarative.
- **Noun-heavy nominal style** for labels and table headers — `대시보드`, `감사업무`, `템플릿`, `내부회계`, `설정`.
- **Verb-final for actions on buttons** — `추가`, `저장`, `삭제`, `생성`, `취소`, `확인`.
- **Terse empty states** — `마감일이 설정된 할일이 없습니다`, `검색 결과가 없습니다`, `알림이 없습니다`.
- Confirmation / error messages in straightforward formal-neutral — `생성에 실패했습니다. 콘솔을 확인해주세요.`, `할일 생성에 실패했습니다.`

### Casing & mixed script

- **Korean labels** for all UI chrome.
- **English caps** for finance/tech acronyms: `FY`, `ICFR`, `PBC`, `CSV`, `xlsx`, `SQLite`.
- **D-Day notation**: `D-7`, `D-Day`, `D+3` (overdue uses `+`). This is used everywhere deadlines appear.
- **Dates**: `YYYY-MM-DD` in tables and badges, `YYYY년 M월` in calendar headers, `YYYY년 M월 D일` in full-date subtitles.

### Pronouns

- No "I"/"you". The UI speaks about *objects* (할일, 클라이언트, 감사), not the user.
- No emoji. No exclamation points. No marketing copy. No "let's", no "great job".

### Icon hinting

- Status badges combine a short Korean word + a background color chip: `미착수`, `진행중`, `검토대기`, `완료`.
- Priority uses single-char labels: `상` / `중` / `하` with a colored dot.
- Industry chips appear as pill-shaped light gray tags: `제조업`, `IT서비스`, `유통업`.

### Examples (lifted from source)

| Surface | Copy |
|---|---|
| Sidebar nav | `대시보드` · `감사업무` · `템플릿` · `내부회계` · `설정` |
| Dashboard H1 | `대시보드` · subtitle `{N}개 클라이언트 감사 현황 요약` |
| Primary CTA (header) | `새 감사업무` |
| Stat card label | `전체 감사 진척률` / `미처리 항목` / `내부회계 테스트 완료율` |
| Search placeholder | `검색... (Ctrl+K)` |
| Empty search | `검색 결과가 없습니다` |
| Keyboard hints | `↑↓ 이동` · `Enter 선택` · `Esc 닫기` |
| Startup alert | `오늘의 알림` · `오늘은 그만 보기` |
| Quick-add hint | `날짜 더블클릭으로 할일 빠른 추가` |

---

## Visual Foundations

### Color

A **Material 3-style navy palette** with surface-container elevations. No gradients except one subtle two-stop on the primary CTA and progress bars.

- **Primary**: `#001e40` (deep navy) — logo, active nav, primary button, progress fill.
- **Primary container**: `#003366` — paired with primary on gradients and CTAs.
- **Primary fixed**: `#d5e3ff` — soft blue tint for in-progress chips, selected search rows, info wells.
- **Secondary**: `#48626e` — muted slate used for client avatars, secondary dots.
- **On-tertiary-container**: `#ff6c63` — the *accent* coral/salmon used for review / warning states.
- **Tertiary fixed**: `#ffdad6` — pale peach background paired with `#ff6c63`.
- **Error**: `#ba1a1a` — overdue deadlines, destructive buttons, overdue D-Day badges.
- **Secondary container**: `#cbe7f5` / on: `#4e6874` — "완료" (done) chip background.
- **Background**: `#f8f9fa` (app background). **Surface container lowest** `#ffffff` (cards). **Low** `#f3f4f5`, default `#edeeef`, highest `#e1e3e4` (progress track).
- **On-surface**: `#191c1d` (primary text). **On-surface-variant**: `#43474f` (secondary text). **Outline**: `#737780`, **Outline-variant**: `#c3c6d1`.

Semantic color usage is strict: only `error` means overdue, only `on-tertiary-container` (coral) means "review / this week", only `primary` means active/in-progress.

### Type

- **Manrope** (200–800) — `font-headline`, used for H1/H2, stat numbers, section titles. Bold (700) for the logo and most headings.
- **Inter** (100–900, optical 14–32) — `font-body` for paragraphs, `font-label` for every label, chip, table cell, and button.
- **Material Symbols Outlined** — single-line monospace-ish glyph font for all iconography.

Sizes skew **small & dense**: app chrome uses 10–14px; stat numbers use `text-2xl` / `text-4xl` (24–36px). Tracking is default; headings occasionally use `tracking-tight`.

### Spacing & radii

- 4 / 8 / 12 / 16 / 20 / 24px rhythm (Tailwind default).
- Radii are **overloaded**: Tailwind's `rounded-xl` is remapped to `0.5rem` and is the workhorse; `rounded-full` is remapped to `0.75rem` (NOT actually pill — it's a soft-square). True pills use `rounded-full` only on circular avatars and dots.
- Cards: `rounded-xl` + `border border-outline-variant` + white (`surface-container-lowest`) background, usually `p-5`.

### Backgrounds, textures, imagery

- **No photographs. No illustrations. No gradients as background.**
- Only the navy gradient (`from-primary to-primary-container`) on the primary CTA and progress-bar fill — it's a 2-stop 90° gradient.
- Startup-alert modal uses a `backdrop-blur-sm` black/30 overlay; regular modals use plain `black/40`.
- Header has a translucent `bg-surface-container-lowest/80 backdrop-blur-md` — subtle glass effect on scroll.

### Shadows

- Almost none, by design. Cards have a **1px border** (`outline-variant` `#c3c6d1`) instead of drop shadow.
- Active sidebar item uses `shadow-sm` on a white pill — a single faint shadow is the affordance.
- Modals use `shadow-2xl` — only other shadow system in the product.

### Borders

- `border border-outline-variant` (`#c3c6d1`) everywhere — 1px.
- Stat cards sometimes add a colored left stripe: `border-l-4 border-l-error` (for the "미처리 항목" card). This is the **one** time a colored left border is used — do not invent new ones.
- Divider hairlines inside cards use `border-outline-variant/50`.

### States

- **Hover**: background darkens one step — `hover:bg-surface-container` (from `surface-container-low` / white). Primary buttons use `hover:opacity-90`.
- **Active/selected**: nav items flip to white pill + `shadow-sm` + `text-primary font-semibold`. Tree nodes do the same.
- **Focus**: inputs get `focus:border-primary focus:outline-none`; sometimes `focus:ring-1 focus:ring-primary`.
- **Transitions**: `transition` / `transition-all duration-200` (nav) or `duration-700` (progress bars animating on mount). No springy physics.
- **Disabled**: not widely expressed — reduce opacity and remove hover.

### Layout rules

- Sidebar **fixed** at `w-64` on `lg:` breakpoint; off-canvas with overlay below.
- Header **sticky** at `h-14`, backdrop-blurred.
- Main content padded `p-4` / `lg:p-6`.
- Grid-heavy: `grid-cols-1 md:grid-cols-3` for stat rows, `grid-cols-1 lg:grid-cols-3` for the dashboard body.
- Dense tables with `border-b border-outline-variant` between rows, no zebra striping.

### Transparency & blur

- **Translucent sticky header** — `bg-surface-container-lowest/80 backdrop-blur-md`.
- **Modal scrims** — `bg-black/40` or `bg-black/30 backdrop-blur-sm` (startup alert only).
- **Soft chip backgrounds** — many chips use `bg-error/10`, `bg-primary/10`, `bg-on-tertiary-container/10` — 10% tints on the semantic color.

### Corner radii (the short version)

- Chips / small buttons: `rounded-lg` (`0.25rem`).
- Buttons / inputs / nav items / cards / chips / most everything else: `rounded-xl` (`0.5rem`).
- Modals: `rounded-2xl` (`1rem` — Tailwind default).
- Avatars and notification dots: `rounded-full`.

### Cards

- White surface `#ffffff` + `border border-outline-variant` + `rounded-xl` + `p-5`.
- Never two shadows. Never a colored background (except stat cards with a left accent).
- Section headings inside cards are `font-headline text-base font-bold text-on-surface`. Secondary metadata is `text-xs font-label text-outline`.

---

## Iconography

**Primary system**: Google's **Material Symbols Outlined** variable web font, loaded from Google Fonts. Used as class `.material-symbols-outlined` with font-variation-settings for fill/weight/grade/optical-size.

```css
.material-symbols-outlined {
  font-variation-settings:
    "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24;
}
```

Icons in code are referenced by glyph name, e.g.:

```jsx
<span className="material-symbols-outlined text-[20px]">dashboard</span>
```

**Commonly-used glyphs** (from audit of codebase):
`verified` (logo), `dashboard`, `work`, `description`, `fact_check`, `settings`, `search`, `notifications`, `notifications_active`, `notifications_off`, `menu`, `close`, `add`, `add_task`, `add_business`, `check`, `check_circle`, `chevron_left`, `chevron_right`, `business`, `account_balance`, `folder`, `calendar_today`, `task_alt`, `radio_button_unchecked`, `pending`, `rate_review`, `error`, `today`, `date_range`, `info`, `progress_activity`, `search_off`, `help`.

- **No emoji.** Not in strings, not in icons, not in copy.
- **No custom SVG icons.** The single custom SVG is `public/favicon.svg`, which (as noted) is from a different project and not part of AuditLink's real identity.
- **No PNG icons.** All iconography is font-glyph.
- **No Unicode drawing characters** (no ▲/●/★, etc.).

Sizing conventions: `text-[16px]` for inline inside labels, `text-[18–20px]` for nav/header actions, `text-[22px]` for mobile menu, `text-xl`/`text-2xl` for modal heros. Color is always inherited from the parent (`text-primary`, `text-on-surface-variant`, `text-error`, etc.).

**This design system uses Material Symbols Outlined from Google Fonts as-is.** No CDN substitution was needed. If offline bundling is ever required, swap to the self-hosted variable font file of the same family.

---

## Products represented

There is one product: **AuditLink desktop app** (Korean). It has five main surfaces, all wrapped in the same `Layout` (sidebar + sticky header):

1. **Dashboard** (`/`) — progress ring, stat cards, deadlines list, engagements table, monthly/weekly calendar.
2. **Engagements** (`/engagements`) — 3-pane: tree (FY → Client → Phase → Account), task list/kanban, detail panel. Also hosts Client Summary and PBC panels.
3. **Templates** (`/templates`) — industry-tagged audit template cards (제조업, IT서비스업, 유통업) + a CSV checklist importer.
4. **ICFR** (`/icfr`) — internal-control test tracking table with client and status filters.
5. **Settings** (`/settings`) — FY management, profile, deadline reminder rules, data backup/restore/reset.

The UI kit recreates core components for all five surfaces.
