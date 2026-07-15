export const STATUS = {
  todo:        { label: "미착수",   color: "#9ca3af" },
  in_progress: { label: "진행중",   color: "#3b82f6" },
  review:      { label: "검토대기", color: "#f59e0b" },
  done:        { label: "완료",     color: "#10b981" },
  exception:   { label: "예외발견", color: "#ef4444" },
  overdue:     { label: "마감초과", color: "#ef4444" },
};

export const PRIORITY = {
  high: { label: "상", color: "#ef4444" },
  mid:  { label: "중", color: "#f59e0b" },
  low:  { label: "하", color: "#9ca3af" },
};

export const ENG_TYPE = {
  audit:  { label: "감사", color: "#3b82f6" },
  review: { label: "검토", color: "#10b981" },
  etc:    { label: "기타", color: "#9ca3af" },
};

export const NAV = [
  { key: "dashboard",   icon: "dashboard",   label: "대시보드" },
  { key: "engagements", icon: "work",        label: "감사업무" },
  { key: "icfr",        icon: "fact_check",  label: "내부회계" },
  { key: "templates",   icon: "description", label: "템플릿"   },
  { key: "settings",    icon: "settings",    label: "설정"     },
];
