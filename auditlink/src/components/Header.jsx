import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

function NewEngagementModal({ open, onClose }) {
  const navigate = useNavigate();
  const [fiscalYears, setFiscalYears] = useState([]);
  const [form, setForm] = useState({
    fy_id: "",
    name: "",
    industry: "",
    report_date: "",
    submit_date: "",
  });

  useEffect(() => {
    if (!open) return;
    api.getFiscalYears().then((fys) => {
      setFiscalYears(fys);
      if (fys.length) setForm((f) => ({ ...f, fy_id: String(fys[0].id) }));
    }).catch(() => {});
  }, [open]);

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    try {
      const client = await api.createClient({
        fy_id: Number(form.fy_id),
        name: form.name.trim(),
        industry: form.industry.trim(),
        report_date: form.report_date || null,
      });
      // Create default phases
      await api.createPhase({ client_id: client.id, name: "기중감사", sort_order: 0 });
      await api.createPhase({ client_id: client.id, name: "기말감사", sort_order: 1 });
      onClose();
      navigate("/engagements");
    } catch {
      alert("생성에 실패했습니다.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <form
        onSubmit={handleSubmit}
        className="relative bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl w-full max-w-lg flex flex-col overflow-hidden"
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b border-outline-variant">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-xl">add_business</span>
            </div>
            <h3 className="font-headline text-lg font-bold text-on-surface">새 감사업무</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-9 h-9 rounded-xl flex items-center justify-center hover:bg-surface-container transition"
          >
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        {/* 본문 */}
        <div className="p-6 space-y-4">
          {/* 회계연도 */}
          <label className="block">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">회계연도 (FY)</span>
            <select
              value={form.fy_id}
              onChange={(e) => setForm({ ...form, fy_id: e.target.value })}
              className="appearance-none w-full pl-3 pr-8 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-label text-on-surface cursor-pointer focus:border-primary focus:outline-none transition"
            >
              {fiscalYears.map((fy) => (
                <option key={fy.id} value={fy.id}>{fy.name}</option>
              ))}
            </select>
          </label>

          {/* 클라이언트명 */}
          <label className="block">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">클라이언트명 *</span>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="예: 한빛제조"
              className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition"
            />
          </label>

          {/* 업종 */}
          <label className="block">
            <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">업종</span>
            <input
              type="text"
              value={form.industry}
              onChange={(e) => setForm({ ...form, industry: e.target.value })}
              placeholder="예: 제조업, IT서비스, 유통업"
              className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface placeholder:text-outline focus:border-primary focus:outline-none transition"
            />
          </label>

          <div className="grid grid-cols-2 gap-4">
            {/* 결산일 */}
            <label className="block">
              <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">결산일</span>
              <input
                type="date"
                value={form.report_date}
                onChange={(e) => setForm({ ...form, report_date: e.target.value })}
                className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition"
              />
            </label>

            {/* 감사보고서 제출일 */}
            <label className="block">
              <span className="text-xs font-label font-semibold text-on-surface-variant mb-1.5 block">감사보고서 제출일</span>
              <input
                type="date"
                value={form.submit_date}
                onChange={(e) => setForm({ ...form, submit_date: e.target.value })}
                className="w-full px-3 py-2.5 rounded-xl border border-outline-variant bg-surface-container-lowest text-sm font-body text-on-surface focus:border-primary focus:outline-none transition"
              />
            </label>
          </div>
        </div>

        {/* 푸터 */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-outline-variant">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl border border-outline-variant text-sm font-label font-semibold text-on-surface-variant hover:bg-surface-container transition"
          >
            취소
          </button>
          <button
            type="submit"
            className="px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-label font-semibold hover:opacity-90 transition flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-base">check</span>
            생성
          </button>
        </div>
      </form>
    </div>
  );
}

export default function Header({ onMenuToggle }) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-20 h-14 bg-surface-container-lowest/80 backdrop-blur-md border-b border-outline-variant flex items-center justify-between px-4 lg:px-6">
        {/* Left: hamburger + search */}
        <div className="flex items-center gap-2">
          <button
            onClick={onMenuToggle}
            className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition lg:hidden"
          >
            <span className="material-symbols-outlined text-[22px]">menu</span>
          </button>
          <div className="relative w-48 sm:w-64 lg:w-80">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">
              search
            </span>
            <input
              type="text"
              placeholder="검색..."
              className="w-full pl-10 pr-4 py-2 text-sm font-body bg-surface-container rounded-xl border border-outline-variant placeholder:text-outline focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition"
            />
          </div>
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-1 sm:gap-2">
          <button className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition hidden sm:flex">
            <span className="material-symbols-outlined text-[20px]">notifications</span>
          </button>
          <button className="p-2 rounded-xl text-on-surface-variant hover:bg-surface-container transition hidden sm:flex">
            <span className="material-symbols-outlined text-[20px]">help</span>
          </button>

          <button
            onClick={() => setModalOpen(true)}
            className="ml-1 sm:ml-2 px-3 sm:px-4 py-2 bg-gradient-to-r from-primary to-primary-container text-white text-xs sm:text-sm font-label font-semibold rounded-xl hover:opacity-90 transition flex items-center gap-1.5"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            <span className="hidden sm:inline">새 감사업무</span>
          </button>

          <div className="ml-1 sm:ml-2 w-8 h-8 rounded-full bg-primary-container flex items-center justify-center">
            <span className="text-xs font-label font-bold text-white">감</span>
          </div>
        </div>
      </header>

      <NewEngagementModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </>
  );
}
