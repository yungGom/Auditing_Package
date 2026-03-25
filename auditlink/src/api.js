/**
 * Thin wrapper around fetch for the AuditLink backend.
 * Base URL defaults to localhost:8000 during dev.
 */
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, opts = {}) {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${url}`);
  return res.json();
}

const api = {
  // Fiscal Years
  getFiscalYears: () => request("/api/fiscal-years"),
  createFiscalYear: (data) => request("/api/fiscal-years", { method: "POST", body: JSON.stringify(data) }),
  updateFiscalYear: (id, data) => request(`/api/fiscal-years/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteFiscalYear: (id) => request(`/api/fiscal-years/${id}`, { method: "DELETE" }),

  // Clients
  getClients: (fyId) => request(`/api/clients${fyId ? `?fy_id=${fyId}` : ""}`),
  createClient: (data) => request("/api/clients", { method: "POST", body: JSON.stringify(data) }),
  updateClient: (id, data) => request(`/api/clients/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteClient: (id) => request(`/api/clients/${id}`, { method: "DELETE" }),

  // Phases
  getPhases: (clientId) => request(`/api/phases${clientId ? `?client_id=${clientId}` : ""}`),
  createPhase: (data) => request("/api/phases", { method: "POST", body: JSON.stringify(data) }),
  deletePhase: (id) => request(`/api/phases/${id}`, { method: "DELETE" }),

  // Accounts
  getAccounts: (phaseId) => request(`/api/accounts${phaseId ? `?phase_id=${phaseId}` : ""}`),
  createAccount: (data) => request("/api/accounts", { method: "POST", body: JSON.stringify(data) }),
  deleteAccount: (id) => request(`/api/accounts/${id}`, { method: "DELETE" }),

  // Tasks
  getTasks: (accountId) => request(`/api/tasks${accountId ? `?account_id=${accountId}` : ""}`),
  getTask: (id) => request(`/api/tasks/${id}`),
  createTask: (data) => request("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
  updateTask: (id, data) => request(`/api/tasks/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteTask: (id) => request(`/api/tasks/${id}`, { method: "DELETE" }),
  getTaskHistory: (id) => request(`/api/tasks/${id}/history`),

  // Templates
  getTemplates: () => request("/api/templates"),
  createTemplate: (data) => request("/api/templates", { method: "POST", body: JSON.stringify(data) }),
  updateTemplate: (id, data) => request(`/api/templates/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteTemplate: (id) => request(`/api/templates/${id}`, { method: "DELETE" }),

  // ICFR
  getICFRTests: (params) => {
    const sp = new URLSearchParams();
    if (params?.client_name) sp.set("client_name", params.client_name);
    if (params?.status) sp.set("status", params.status);
    const qs = sp.toString();
    return request(`/api/icfr-tests${qs ? `?${qs}` : ""}`);
  },
  createICFRTest: (data) => request("/api/icfr-tests", { method: "POST", body: JSON.stringify(data) }),
  updateICFRTest: (id, data) => request(`/api/icfr-tests/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteICFRTest: (id) => request(`/api/icfr-tests/${id}`, { method: "DELETE" }),

  // Settings
  getSettings: () => request("/api/settings"),
  updateSettings: (data) => request("/api/settings", { method: "PUT", body: JSON.stringify(data) }),

  // Search
  search: (q) => request(`/api/search?q=${encodeURIComponent(q)}`),

  // Dashboard
  getDashboard: () => request("/api/dashboard"),

  // Engagement tree
  getEngagementTree: () => request("/api/engagement-tree"),
};

export default api;
