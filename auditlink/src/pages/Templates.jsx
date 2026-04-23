// ---------------------------------------------------------------------------
// Templates – 감사 템플릿 관리 페이지
// ---------------------------------------------------------------------------
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import ExcelChecklist from "../components/ExcelChecklist";

const MOCK_TEMPLATES = [
  {
    id: 1,
    name: "제조업 기본",
    industry: "제조업",
    updatedAt: "2025-03-15",
    accounts: [
      {
        name: "매출채권",
        tasks: ["매출채권 확인서 발송", "대손충당금 적정성 검토", "매출채권 연령분석"],
      },
      {
        name: "재고자산",
        tasks: ["재고실사 참관", "재고자산 평가 검토", "저가법 적용 검토"],
      },
      {
        name: "유형자산",
        tasks: ["유형자산 실사", "감가상각비 재계산", "손상차손 검토"],
      },
      {
        name: "매입채무",
        tasks: ["매입채무 확인서 발송", "기말 미지급금 검토"],
      },
      {
        name: "리스",
        tasks: ["리스 계약 검토", "사용권자산/리스부채 재계산"],
      },
      {
        name: "충당부채",
        tasks: ["소송충당부채 검토", "제품보증충당부채 추정 검토"],
      },
    ],
  },
  {
    id: 2,
    name: "IT서비스업",
    industry: "IT서비스",
    updatedAt: "2025-03-10",
    accounts: [
      {
        name: "매출채권",
        tasks: ["매출채권 확인서 발송", "대손충당금 적정성 검토"],
      },
      {
        name: "무형자산",
        tasks: ["개발비 자본화 요건 검토", "무형자산 손상 검토", "내용연수 적정성 검토"],
      },
      {
        name: "선수수익",
        tasks: ["수익인식 기준 검토", "이연수익 적정성 검토"],
      },
      {
        name: "전환사채",
        tasks: ["전환사채 공정가치 평가", "파생상품 분리회계 검토"],
      },
      {
        name: "스톡옵션",
        tasks: ["주식보상비용 재계산", "공정가치 산정 검토"],
      },
    ],
  },
  {
    id: 3,
    name: "유통업",
    industry: "유통업",
    updatedAt: "2025-02-28",
    accounts: [
      {
        name: "매출채권",
        tasks: ["매출채권 확인서 발송", "대손충당금 적정성 검토"],
      },
      {
        name: "재고자산",
        tasks: ["재고실사 참관", "재고자산 평가 검토", "저가법 적용 검토"],
      },
      {
        name: "매입채무",
        tasks: ["매입채무 확인서 발송", "기말 미지급금 검토"],
      },
      {
        name: "리스",
        tasks: ["리스 계약 검토", "사용권자산/리스부채 재계산"],
      },
      {
        name: "충성고객포인트",
        tasks: ["포인트 부채 추정 검토", "사용률 분석 검토"],
      },
    ],
  },
];

const INDUSTRY_COLORS = {
  "제조업": { bg: "bg-primary/10", text: "text-primary", border: "border-primary/20" },
  "IT서비스": { bg: "bg-secondary/10", text: "text-secondary", border: "border-secondary/20" },
  "유통업": { bg: "bg-on-tertiary-container/10", text: "text-on-tertiary-container", border: "border-on-tertiary-container/20" },
};

// --- Sub-components ---------------------------------------------------------

function TemplateCard({ template, onSelect, onDelete, onChecklist }) {
  const colors = INDUSTRY_COLORS[template.industry] || INDUSTRY_COLORS["제조업"];

  return (
    <div
      onClick={() => onSelect(template)}
      className="bg-surface-container-lowest rounded-xl border border-outline-variant p-5 flex flex-col gap-4 cursor-pointer hover:border-primary/40 hover:shadow-md transition-all group"
    >
      {/* 헤더 */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <span className="material-symbols-outlined text-primary text-xl">description</span>
          </div>
          <div>
            <h3 className="text-sm font-label font-bold text-on-surface group-hover:text-primary transition-colors">
              {template.name}
            </h3>
            <span
              className={`inline-block mt-1 text-[11px] font-label font-semibold px-2 py-0.5 rounded-xl border ${colors.bg} ${colors.text} ${colors.border}`}
            >
              {template.industry}
            </span>
          </div>
        </div>
      </div>

      {/* 정보 */}
      <div className="flex items-center justify-between text-xs font-label text-on-surface-variant">
        <div className="flex items-center gap-1.5">
          <span className="material-symbols-outlined text-base">account_tree</span>
          <span>계정과목 <strong className="text-on-surface">{template.accounts.length}</strong>개</span>
        </div>
        <span>{template.updatedAt}</span>
      </div>

      {/* 계정과목 태그 미리보기 */}
      <div className="flex flex-wrap gap-1.5">
        {template.accounts.slice(0, 4).map((acc) => (
          <span
            key={acc.name}
            className="text-[11px] font-label text-on-surface-variant px-2 py-0.5 bg-surface-container rounded-lg"
          >
            {acc.name}
          </span>
        ))}
        {template.accounts.length > 4 && (
          <span className="text-[11px] font-label text-outline px-2 py-0.5">
            +{template.accounts.length - 4}
          </span>
        )}
      </div>

      {/* 버튼 */}
      <div className="flex gap-2 mt-auto pt-2 border-t border-outline-variant/50">
        <button
          onClick={(e) => { e.stopPropagation(); onChecklist?.(template); }}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-primary text-white text-xs font-label font-semibold hover:bg-primary-container hover:text-white transition"
        >
          <span className="material-symbols-outlined text-base">checklist</span>
          체크리스트
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onSelect(template); }}
          className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl border border-outline-variant text-on-surface-variant text-xs font-label font-semibold hover:bg-surface-container transition"
        >
          <span className="material-symbols-outlined text-base">edit</span>
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete?.(template); }}
          className="flex items-center justify-center px-2.5 py-2 rounded-xl border border-outline-variant text-on-surface-variant text-xs hover:bg-error/10 hover:text-error hover:border-error/30 transition"
        >
          <span className="material-symbols-outlined text-base">delete</span>
        </button>
      </div>
    </div>
  );
}

function TemplateDetail({ template, onClose, onApply }) {
  const colors = INDUSTRY_COLORS[template.industry] || INDUSTRY_COLORS["제조업"];
  const totalTasks = template.accounts.reduce((sum, acc) => sum + acc.tasks.length, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      {/* 오버레이 */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* 모달 */}
      <div className="relative bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden">
        {/* 모달 헤더 */}
        <div className="flex items-center justify-between p-6 border-b border-outline-variant">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-2xl">description</span>
            </div>
            <div>
              <h3 className="font-headline text-lg font-bold text-on-surface">{template.name}</h3>
              <div className="flex items-center gap-3 mt-1">
                <span
                  className={`text-[11px] font-label font-semibold px-2 py-0.5 rounded-xl border ${colors.bg} ${colors.text} ${colors.border}`}
                >
                  {template.industry}
                </span>
                <span className="text-xs text-on-surface-variant font-label">
                  계정과목 {template.accounts.length}개 · 할일 {totalTasks}개
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-xl flex items-center justify-center hover:bg-surface-container transition"
          >
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        {/* 모달 본문 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {template.accounts.map((account, idx) => (
            <div
              key={account.name}
              className="rounded-xl border border-outline-variant bg-surface-container-low p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <span className="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center text-xs font-label font-bold text-primary">
                  {idx + 1}
                </span>
                <h4 className="text-sm font-label font-bold text-on-surface">{account.name}</h4>
                <span className="text-[11px] font-label text-on-surface-variant ml-auto">
                  {account.tasks.length}개 할일
                </span>
              </div>
              <ul className="space-y-1.5">
                {account.tasks.map((task) => (
                  <li key={task} className="flex items-center gap-2 text-xs font-body text-on-surface-variant">
                    <span className="material-symbols-outlined text-sm text-outline">check_circle</span>
                    {task}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* 모달 푸터 */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-outline-variant">
          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl border border-outline-variant text-sm font-label font-semibold text-on-surface-variant hover:bg-surface-container transition"
          >
            닫기
          </button>
          <button onClick={() => { onApply(template); onClose(); }}
            className="px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-label font-semibold hover:bg-primary-container hover:text-white transition flex items-center gap-2">
            <span className="material-symbols-outlined text-base">play_arrow</span>
            이 템플릿 적용
          </button>
        </div>
      </div>
    </div>
  );
}

// --- Main -------------------------------------------------------------------

export default function Templates() {
  const navigate = useNavigate();
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [loadError, setLoadError] = useState(false);
  const [checklistOpen, setChecklistOpen] = useState(false);
  const [checklistTemplateId, setChecklistTemplateId] = useState(null);

  useEffect(() => {
    api.getTemplates().then((data) => {
      setTemplates(data || []);
    }).catch(() => { setLoadError(true); });
  }, []);

  const handleDelete = async (tpl) => {
    if (!confirm(`"${tpl.name}" 템플릿을 삭제하시겠습니까?`)) return;
    try {
      await api.deleteTemplate(tpl.id);
      setTemplates((prev) => prev.filter((t) => t.id !== tpl.id));
    } catch { alert("삭제에 실패했습니다."); }
  };

  const handleApply = (tpl) => {
    // Navigate to engagements with template info so user can pick a client to apply to
    alert(`"${tpl.name}" 템플릿을 적용하려면 감사업무 페이지에서 클라이언트를 선택 후 요청자료 탭의 "엑셀 가져오기"를 사용하세요.\n\n또는 감사업무 트리에서 Phase 우클릭 → "계정과목 일괄 추가"로 이 템플릿의 계정과목을 추가할 수 있습니다.`);
    navigate("/engagements");
  };

  return (
    <div className="space-y-6">
      {/* 상단 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-headline text-2xl font-bold text-on-surface">감사 템플릿</h2>
          <p className="mt-1 text-sm text-on-surface-variant font-body">
            업종별 감사 템플릿을 관리하고 새로운 감사에 적용하세요
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setChecklistTemplateId(null); setChecklistOpen(true); }}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-outline-variant text-on-surface-variant text-sm font-label font-semibold hover:bg-surface-container transition"
          >
            <span className="material-symbols-outlined text-lg">upload_file</span>
            템플릿 가져오기
          </button>
          <button
            onClick={() => {
              const name = prompt("새 템플릿 이름:");
              if (!name) return;
              const industry = prompt("업종 (예: 제조업, IT서비스):") || "";
              api.createTemplate({ name, industry, accounts_json: "[]", updated_at: new Date().toISOString().slice(0, 10) })
                .then((created) => { setTemplates((prev) => [...prev, { ...created, accounts: [] }]); })
                .catch(() => alert("템플릿 생성에 실패했습니다."));
            }}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-label font-semibold hover:bg-primary-container hover:text-white transition shadow-sm"
          >
            <span className="material-symbols-outlined text-lg">add</span>
            새 템플릿
          </button>
        </div>
      </div>

      {loadError && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-error/10 border border-error/20 text-xs font-label text-error">
          <span className="material-symbols-outlined text-sm">error</span>
          템플릿을 불러오지 못했습니다. 백엔드 서버를 확인해주세요.
        </div>
      )}

      {/* 카드 그리드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-5">
        {templates.map((tpl) => (
          <TemplateCard key={tpl.id} template={tpl} onSelect={setSelectedTemplate} onDelete={handleDelete}
            onChecklist={(t) => { setChecklistTemplateId(t.id); setChecklistOpen(true); }} />
        ))}
      </div>

      {/* 상세 모달 */}
      {selectedTemplate && (
        <TemplateDetail
          template={selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
          onApply={handleApply}
        />
      )}

      {/* 엑셀 체크리스트 */}
      {checklistOpen && (
        <ExcelChecklist
          templateId={checklistTemplateId}
          onClose={() => setChecklistOpen(false)}
        />
      )}
    </div>
  );
}
