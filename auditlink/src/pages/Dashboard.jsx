// ---------------------------------------------------------------------------
// Dashboard – 대시보드 메인 페이지
// ---------------------------------------------------------------------------

const MOCK_DEADLINES = [
  { id: 1, dDay: 3, task: "매출채권 확인서 발송", client: "한빛제조", date: "2025-03-26" },
  { id: 2, dDay: 7, task: "재고실사 참관", client: "서현테크", date: "2025-03-30" },
  { id: 3, dDay: 12, task: "충당부채 검토", client: "동아리테일", date: "2025-04-04" },
  { id: 4, dDay: 25, task: "수익인식 테스트", client: "미래에너지", date: "2025-04-17" },
  { id: 5, dDay: 30, task: "기말감사 보고서 제출", client: "한빛제조", date: "2025-04-22" },
];

const MOCK_ENGAGEMENTS = [
  { id: 1, name: "한빛제조", initials: "한빛", industry: "제조업", progress: 72, nextDeadline: "2025-03-26", color: "bg-primary" },
  { id: 2, name: "서현테크", initials: "서현", industry: "IT서비스", progress: 45, nextDeadline: "2025-03-30", color: "bg-secondary" },
  { id: 3, name: "동아리테일", initials: "동아", industry: "유통업", progress: 88, nextDeadline: "2025-04-04", color: "bg-on-tertiary-container" },
  { id: 4, name: "미래에너지", initials: "미래", industry: "에너지", progress: 31, nextDeadline: "2025-04-17", color: "bg-primary-container" },
];

// --- Helpers ----------------------------------------------------------------

function dDayBadge(d) {
  if (d <= 7) return { bg: "bg-error/10", text: "text-error", border: "border-error/30" };
  if (d <= 15) return { bg: "bg-on-tertiary-container/10", text: "text-on-tertiary-container", border: "border-on-tertiary-container/30" };
  return { bg: "bg-secondary/10", text: "text-secondary", border: "border-secondary/30" };
}

// --- Sub-components ---------------------------------------------------------

function CircularProgress({ value, size = 120, strokeWidth = 10 }) {
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (value / 100) * circumference;

  return (
    <svg width={size} height={size} className="block">
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke="#e1e3e4" strokeWidth={strokeWidth}
      />
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke="#001e40" strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        className="transition-all duration-700"
      />
      <text
        x="50%" y="50%"
        textAnchor="middle" dominantBaseline="central"
        className="fill-on-surface font-headline text-2xl font-bold"
      >
        {value}%
      </text>
    </svg>
  );
}

function StatCards() {
  return (
    <div className="grid grid-cols-3 gap-5">
      {/* 전체 감사 진척률 */}
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 flex flex-col items-center gap-3">
        <h3 className="text-sm font-label font-semibold text-on-surface-variant w-full">
          전체 감사 진척률
        </h3>
        <CircularProgress value={64} />
        <p className="text-xs text-outline font-label">4건 진행 중 · 평균 64%</p>
      </div>

      {/* 미처리 항목 */}
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 border-l-4 border-l-error">
        <h3 className="text-sm font-label font-semibold text-on-surface-variant">
          미처리 항목
        </h3>
        <div className="mt-4 flex items-end gap-2">
          <span className="text-4xl font-headline font-bold text-error">12</span>
          <span className="text-sm text-on-surface-variant font-body mb-1">건</span>
        </div>
        <div className="mt-4 space-y-2">
          <div className="flex justify-between text-xs font-label">
            <span className="text-on-surface-variant">확인서 미회수</span>
            <span className="font-semibold text-on-surface">5건</span>
          </div>
          <div className="flex justify-between text-xs font-label">
            <span className="text-on-surface-variant">검토 대기</span>
            <span className="font-semibold text-on-surface">4건</span>
          </div>
          <div className="flex justify-between text-xs font-label">
            <span className="text-on-surface-variant">자료 미수령</span>
            <span className="font-semibold text-on-surface">3건</span>
          </div>
        </div>
      </div>

      {/* 내부회계 테스트 완료율 */}
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5">
        <h3 className="text-sm font-label font-semibold text-on-surface-variant">
          내부회계 테스트 완료율
        </h3>
        <div className="mt-4 flex items-end gap-2">
          <span className="text-4xl font-headline font-bold text-primary">78</span>
          <span className="text-sm text-on-surface-variant font-body mb-1">%</span>
        </div>
        <div className="mt-4">
          <div className="w-full h-2.5 bg-surface-container-highest rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary to-primary-container rounded-full transition-all duration-700"
              style={{ width: "78%" }}
            />
          </div>
          <div className="mt-2 flex justify-between text-xs font-label text-on-surface-variant">
            <span>완료 39건</span>
            <span>전체 50건</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function DeadlinesSection() {
  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline text-base font-bold text-on-surface">주요 마감일</h3>
        <button className="text-xs font-label text-primary font-semibold hover:underline">
          전체보기
        </button>
      </div>

      <div className="space-y-3">
        {MOCK_DEADLINES.map((item) => {
          const badge = dDayBadge(item.dDay);
          return (
            <div
              key={item.id}
              className="flex items-center gap-4 px-4 py-3 rounded-xl bg-surface-container-low hover:bg-surface-container transition"
            >
              <span
                className={`inline-flex items-center justify-center min-w-[52px] px-2 py-1 rounded-xl text-xs font-label font-bold border ${badge.bg} ${badge.text} ${badge.border}`}
              >
                D-{item.dDay}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-label font-semibold text-on-surface truncate">
                  {item.task}
                </p>
                <p className="text-xs text-on-surface-variant font-body">{item.client}</p>
              </div>
              <span className="text-xs text-outline font-label whitespace-nowrap">
                {item.date}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function EngagementsTable() {
  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline text-base font-bold text-on-surface">진행중인 감사</h3>
        <button className="text-xs font-label text-primary font-semibold hover:underline">
          전체보기
        </button>
      </div>

      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-outline-variant text-xs font-label text-on-surface-variant">
            <th className="pb-3 font-semibold">클라이언트</th>
            <th className="pb-3 font-semibold">업종</th>
            <th className="pb-3 font-semibold">진행률</th>
            <th className="pb-3 font-semibold text-right">다음 마감일</th>
          </tr>
        </thead>
        <tbody>
          {MOCK_ENGAGEMENTS.map((e) => (
            <tr
              key={e.id}
              className="border-b border-outline-variant/50 last:border-b-0 hover:bg-surface-container-low transition"
            >
              <td className="py-3.5">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-8 h-8 rounded-full ${e.color} flex items-center justify-center`}
                  >
                    <span className="text-[10px] font-label font-bold text-white">
                      {e.initials.slice(0, 2)}
                    </span>
                  </div>
                  <span className="text-sm font-label font-semibold text-on-surface">
                    {e.name}
                  </span>
                </div>
              </td>
              <td className="py-3.5">
                <span className="text-xs font-label text-on-surface-variant px-2 py-0.5 bg-surface-container rounded-xl">
                  {e.industry}
                </span>
              </td>
              <td className="py-3.5">
                <div className="flex items-center gap-3">
                  <div className="w-24 h-2 bg-surface-container-highest rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all duration-700"
                      style={{ width: `${e.progress}%` }}
                    />
                  </div>
                  <span className="text-xs font-label font-semibold text-on-surface w-8 text-right">
                    {e.progress}%
                  </span>
                </div>
              </td>
              <td className="py-3.5 text-right">
                <span className="text-xs font-label text-on-surface-variant">
                  {e.nextDeadline}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Main -------------------------------------------------------------------

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-headline text-2xl font-bold text-on-surface">대시보드</h2>
        <p className="mt-1 text-sm text-on-surface-variant font-body">
          FY2025 감사 현황 요약
        </p>
      </div>

      <StatCards />

      <div className="grid grid-cols-2 gap-5">
        <DeadlinesSection />
        <EngagementsTable />
      </div>
    </div>
  );
}
