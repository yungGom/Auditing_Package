import { useState, useEffect } from "react";
import api from "../api";

const STATUS_STYLE = {
  "진행중": "bg-primary-fixed text-primary",
  "완료": "bg-secondary-container text-on-secondary-container",
};

// ---------------------------------------------------------------------------
// Interview Detail Slide Panel
// ---------------------------------------------------------------------------

function InterviewDetail({ interview, onClose, onSave, onDelete }) {
  const [form, setForm] = useState({});
  const [questions, setQuestions] = useState([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!interview) return;
    setForm({
      date: interview.date || new Date().toISOString().slice(0, 10),
      interviewee: interview.interviewee || "",
      position: interview.position || "",
      location: interview.location || "",
      attendees: interview.attendees || "",
      topic: interview.topic || "",
      status: interview.status || "진행중",
      memo: interview.memo || "",
    });
    // Load full interview with questions
    if (interview.id) {
      api.getInterview(interview.id).then((full) => {
        setQuestions((full.questions || []).map((q, i) => ({ ...q, _key: i })));
      }).catch(() => setQuestions([]));
    } else {
      setQuestions([]);
    }
    setDirty(false);
  }, [interview]);

  useEffect(() => {
    const h = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  if (!interview) return null;

  const update = (k, v) => { setForm((p) => ({ ...p, [k]: v })); setDirty(true); };
  let nextKey = questions.length + 100;

  const addQuestion = () => {
    setQuestions((prev) => [...prev, {
      _key: nextKey++, order_num: prev.length, question: "", answer: "",
      answerer: form.interviewee, needs_followup: false, followup_note: "",
    }]);
    setDirty(true);
  };

  const updateQ = (idx, patch) => {
    setQuestions((prev) => prev.map((q, i) => i === idx ? { ...q, ...patch } : q));
    setDirty(true);
  };

  const removeQ = (idx) => {
    setQuestions((prev) => prev.filter((_, i) => i !== idx).map((q, i) => ({ ...q, order_num: i })));
    setDirty(true);
  };

  // Drag reorder
  const [dragIdx, setDragIdx] = useState(null);
  const handleDragStart = (i) => setDragIdx(i);
  const handleDragOver = (e, i) => {
    e.preventDefault();
    if (dragIdx === null || dragIdx === i) return;
    setQuestions((prev) => {
      const list = [...prev];
      const [moved] = list.splice(dragIdx, 1);
      list.splice(i, 0, moved);
      return list.map((q, j) => ({ ...q, order_num: j }));
    });
    setDragIdx(i);
    setDirty(true);
  };

  const handleSave = async () => {
    const saved = await onSave(interview.id, form, questions);
    if (saved) setDirty(false);
  };

  // Export to HTML
  const handleExport = () => {
    const qs = questions.map((q, i) => `
      <tr><td style="width:30px;text-align:center;font-weight:bold">Q${i + 1}</td>
      <td style="padding:6px">${esc(q.question)}</td>
      <td style="padding:6px">${esc(q.answer)}</td>
      <td style="padding:6px">${esc(q.answerer)}</td>
      <td style="padding:6px;text-align:center">${q.needs_followup ? "✓" : ""}</td></tr>
      ${q.needs_followup && q.followup_note ? `<tr><td></td><td colspan="4" style="padding:4px 6px;color:#666;font-size:12px">후속조치: ${esc(q.followup_note)}</td></tr>` : ""}
    `).join("");
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>인터뷰 기록</title>
    <style>body{font-family:'Malgun Gothic',sans-serif;padding:30px;max-width:800px;margin:auto}
    table{width:100%;border-collapse:collapse;margin:16px 0}th,td{border:1px solid #ccc;padding:8px;text-align:left;vertical-align:top}
    th{background:#f0f0f0;font-size:13px}h1{font-size:18px;margin-bottom:4px}p{margin:4px 0;font-size:13px;color:#555}</style></head>
    <body><h1>인터뷰 기록 워킹페이퍼</h1>
    <p><b>일자:</b> ${form.date} &nbsp; <b>대상자:</b> ${form.interviewee} (${form.position})</p>
    <p><b>장소:</b> ${form.location} &nbsp; <b>참석자:</b> ${form.attendees}</p>
    <p><b>주제:</b> ${form.topic} &nbsp; <b>상태:</b> ${form.status}</p>
    <table><thead><tr><th>#</th><th>질의사항</th><th>답변사항</th><th>답변자</th><th>후속</th></tr></thead><tbody>${qs}</tbody></table>
    ${form.memo ? `<p style="margin-top:16px"><b>총평/메모:</b><br/>${esc(form.memo).replace(/\n/g, "<br/>")}</p>` : ""}
    </body></html>`;
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url;
    a.download = `인터뷰_${form.interviewee}_${form.date}.html`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40" onClick={onClose} />
      <div className="fixed top-0 right-0 bottom-0 w-full max-w-[640px] bg-surface-container-lowest border-l border-outline-variant shadow-2xl z-50 flex flex-col" style={{ animation: "slideIn 0.2s ease-out" }}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-lg">record_voice_over</span>
            </div>
            <span className="text-sm font-label font-semibold text-on-surface-variant">{interview.id ? "인터뷰 상세" : "새 인터뷰"}</span>
          </div>
          <div className="flex items-center gap-2">
            {interview.id && (
              <button onClick={handleExport} className="px-2.5 py-1.5 rounded-xl border border-outline-variant text-[11px] font-label font-semibold text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">download</span>워드 내보내기
              </button>
            )}
            <button onClick={onClose} className="w-8 h-8 rounded-xl flex items-center justify-center hover:bg-surface-container transition">
              <span className="material-symbols-outlined text-on-surface-variant text-lg">close</span>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {/* Info fields */}
          <div className="bg-surface-container rounded-xl p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="인터뷰 날짜 *" type="date" value={form.date} onChange={(v) => update("date", v)} />
              <div>
                <span className="text-xs font-label font-semibold text-on-surface-variant mb-1 block">상태</span>
                <div className="flex gap-1.5">
                  {["진행중", "완료"].map((s) => (
                    <button key={s} onClick={() => update("status", s)}
                      className={`px-3 py-1.5 rounded-xl text-[11px] font-label font-bold transition ${form.status === s ? (STATUS_STYLE[s] + " ring-1 ring-current") : "bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-low"}`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="인터뷰 대상자 *" value={form.interviewee} onChange={(v) => update("interviewee", v)} placeholder="피감사인 담당자명" />
              <Field label="직책" value={form.position} onChange={(v) => update("position", v)} placeholder="예: 재무팀장" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="장소" value={form.location} onChange={(v) => update("location", v)} placeholder="예: 본사 회의실" />
              <Field label="참석자 (감사팀)" value={form.attendees} onChange={(v) => update("attendees", v)} placeholder="예: 김감사, 박대리" />
            </div>
            <Field label="주제/목적" value={form.topic} onChange={(v) => update("topic", v)} placeholder="인터뷰 주제 한 줄 요약" />
          </div>

          {/* Q&A Section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-headline font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-primary">quiz</span>
                질의응답 ({questions.length}건)
              </h4>
              <button onClick={addQuestion} className="px-2.5 py-1 rounded-xl bg-primary text-white text-[11px] font-label font-semibold hover:opacity-90 transition flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">add</span>질의 추가
              </button>
            </div>

            <div className="space-y-3">
              {questions.map((q, idx) => (
                <div key={q._key ?? q.id ?? idx}
                  draggable onDragStart={() => handleDragStart(idx)} onDragOver={(e) => handleDragOver(e, idx)} onDragEnd={() => setDragIdx(null)}
                  className={`bg-surface-container-lowest rounded-xl border border-outline-variant p-3 ${dragIdx === idx ? "opacity-50" : ""}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-[14px] text-outline cursor-grab">drag_indicator</span>
                    <span className="text-xs font-label font-bold text-primary">Q{idx + 1}</span>
                    <button onClick={() => removeQ(idx)} className="ml-auto p-1 rounded-lg hover:bg-error/10 transition">
                      <span className="material-symbols-outlined text-[14px] text-error">delete</span>
                    </button>
                  </div>
                  <textarea value={q.question} onChange={(e) => updateQ(idx, { question: e.target.value })} rows={2} placeholder="질의사항"
                    className="w-full px-2.5 py-1.5 rounded-lg border border-outline-variant bg-surface-container-lowest text-xs font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition resize-none mb-2" />
                  <textarea value={q.answer} onChange={(e) => updateQ(idx, { answer: e.target.value })} rows={2} placeholder="답변사항"
                    className="w-full px-2.5 py-1.5 rounded-lg border border-outline-variant bg-surface-container-lowest text-xs font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition resize-none mb-2" />
                  <div className="flex items-center gap-3">
                    <input type="text" value={q.answerer} onChange={(e) => updateQ(idx, { answerer: e.target.value })} placeholder="답변자"
                      className="flex-1 px-2.5 py-1 rounded-lg border border-outline-variant bg-surface-container-lowest text-xs font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
                    <label className="flex items-center gap-1.5 text-[11px] font-label text-on-surface-variant cursor-pointer shrink-0">
                      <input type="checkbox" checked={q.needs_followup} onChange={(e) => updateQ(idx, { needs_followup: e.target.checked })}
                        className="w-3.5 h-3.5 rounded border-outline-variant text-primary focus:ring-primary" />
                      후속조치
                    </label>
                  </div>
                  {q.needs_followup && (
                    <textarea value={q.followup_note} onChange={(e) => updateQ(idx, { followup_note: e.target.value })} rows={1} placeholder="후속조치 내용"
                      className="w-full mt-2 px-2.5 py-1.5 rounded-lg border border-on-tertiary-container/30 bg-on-tertiary-container/5 text-xs font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition resize-none" />
                  )}
                </div>
              ))}
              {questions.length === 0 && (
                <p className="text-center py-6 text-xs text-outline font-body">"질의 추가"를 눌러 질의응답을 기록하세요</p>
              )}
            </div>
          </div>

          {/* Memo */}
          <div>
            <label className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">총평/메모</label>
            <textarea value={form.memo} onChange={(e) => update("memo", e.target.value)} rows={3} placeholder="인터뷰 총평, 특이사항 등"
              className="w-full px-3 py-2 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition resize-none" />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-outline-variant shrink-0">
          {interview.id ? (
            <button onClick={() => { if (confirm("이 인터뷰를 삭제하시겠습니까?")) onDelete(interview.id); }}
              className="px-3 py-2 rounded-xl text-xs font-label font-semibold text-error hover:bg-error/5 transition flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">delete</span>삭제
            </button>
          ) : <div />}
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="px-4 py-2 rounded-xl border border-outline-variant text-xs font-label font-semibold text-on-surface-variant hover:bg-surface-container transition">닫기</button>
            <button onClick={handleSave} disabled={!dirty}
              className={`px-5 py-2 rounded-xl text-xs font-label font-semibold text-white transition flex items-center gap-1.5 ${dirty ? "bg-primary hover:opacity-90" : "bg-outline cursor-not-allowed"}`}>
              <span className="material-symbols-outlined text-sm">save</span>저장
            </button>
          </div>
        </div>
      </div>
      <style>{`@keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }`}</style>
    </>
  );
}

function Field({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <label className="block">
      <span className="text-xs font-label font-semibold text-on-surface-variant mb-1 block">{label}</span>
      <input type={type} value={value || ""} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        className="w-full px-2.5 py-1.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-xs font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition" />
    </label>
  );
}

function esc(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

// ---------------------------------------------------------------------------
// Main InterviewPanel
// ---------------------------------------------------------------------------

export default function InterviewPanel({ clientId, accountId, filterByAccount, useApi }) {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState(null);

  const dbClientId = clientId ? parseInt(String(clientId).replace("client-", "")) : null;
  const dbAccountId = accountId && filterByAccount ? parseInt(String(accountId).replace("account-", "")) : null;

  useEffect(() => {
    if (!useApi || !dbClientId) { setLoading(false); return; }
    setLoading(true);
    const params = { client_id: dbClientId };
    if (dbAccountId) params.account_id = dbAccountId;
    api.getInterviews(params).then(setInterviews).catch(() => setInterviews([])).finally(() => setLoading(false));
  }, [dbClientId, dbAccountId, useApi]);

  const handleAdd = () => {
    setDetail({ id: null, client_id: dbClientId, account_id: dbAccountId, date: new Date().toISOString().slice(0, 10), interviewee: "", position: "", location: "", attendees: "", topic: "", status: "진행중", memo: "" });
  };

  const handleSave = async (id, form, questions) => {
    try {
      let interviewId = id;
      if (id) {
        await api.updateInterview(id, form);
      } else {
        const created = await api.createInterview({ client_id: dbClientId, account_id: dbAccountId, ...form });
        interviewId = created.id;
      }
      // Sync questions
      const qBodies = questions.map((q, i) => ({
        interview_id: interviewId, order_num: i,
        question: q.question, answer: q.answer, answerer: q.answerer,
        needs_followup: q.needs_followup, followup_note: q.followup_note,
      }));
      await api.syncInterviewQuestions(interviewId, qBodies);
      // Reload list
      const params = { client_id: dbClientId };
      if (dbAccountId) params.account_id = dbAccountId;
      const updated = await api.getInterviews(params);
      setInterviews(updated);
      setDetail(null);
      return true;
    } catch { alert("저장에 실패했습니다."); return false; }
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteInterview(id);
      setInterviews((prev) => prev.filter((i) => i.id !== id));
      setDetail(null);
    } catch { alert("삭제에 실패했습니다."); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-on-surface-variant font-body">
        <span className="material-symbols-outlined text-2xl animate-spin text-outline-variant mr-2">progress_activity</span>
        불러오는 중...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-on-surface-variant font-label">인터뷰 {interviews.length}건</p>
        <button onClick={handleAdd}
          className="px-3 py-1.5 bg-gradient-to-r from-primary to-primary-container text-white text-xs font-label font-semibold rounded-xl hover:opacity-90 transition flex items-center gap-1">
          <span className="material-symbols-outlined text-[14px]">add</span>인터뷰 추가
        </button>
      </div>

      {/* Card list */}
      <div className="flex-1 overflow-y-auto space-y-2.5">
        {interviews.map((iv) => {
          const st = STATUS_STYLE[iv.status] || STATUS_STYLE["진행중"];
          return (
            <div key={iv.id} onClick={() => setDetail(iv)}
              className="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 hover:shadow-sm hover:border-primary/30 transition cursor-pointer">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs font-label font-bold text-on-surface">{iv.date}</span>
                    <span className={`inline-flex px-2 py-0.5 rounded-xl text-[10px] font-label font-bold ${st}`}>{iv.status}</span>
                  </div>
                  <p className="text-sm font-label font-semibold text-on-surface truncate">{iv.interviewee}{iv.position ? ` (${iv.position})` : ""}</p>
                  {iv.topic && <p className="text-xs text-on-surface-variant font-body mt-0.5 truncate">{iv.topic}</p>}
                </div>
                <div className="text-right shrink-0">
                  <span className="text-[11px] font-label text-on-surface-variant flex items-center gap-1">
                    <span className="material-symbols-outlined text-[14px]">quiz</span>
                    질의 {iv.question_count || 0}건
                  </span>
                </div>
              </div>
            </div>
          );
        })}
        {interviews.length === 0 && (
          <div className="text-center py-10 text-on-surface-variant text-sm font-body">인터뷰 기록이 없습니다</div>
        )}
      </div>

      {/* Detail panel */}
      {detail && (
        <InterviewDetail interview={detail} onClose={() => setDetail(null)} onSave={handleSave} onDelete={handleDelete} />
      )}
    </div>
  );
}
