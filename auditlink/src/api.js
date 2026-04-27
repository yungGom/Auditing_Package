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
  getClientSummary: (id) => request(`/api/clients/${id}/summary`),
  getClientOverview: (id) => request(`/api/clients/${id}/overview`),
  createClient: (data) => request("/api/clients", { method: "POST", body: JSON.stringify(data) }),
  updateClient: (id, data) => request(`/api/clients/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteClient: (id) => request(`/api/clients/${id}`, { method: "DELETE" }),

  // Phases
  getPhases: (clientId) => request(`/api/phases${clientId ? `?client_id=${clientId}` : ""}`),
  createPhase: (data) => request("/api/phases", { method: "POST", body: JSON.stringify(data) }),
  deletePhase: (id) => request(`/api/phases/${id}`, { method: "DELETE" }),

  // Account Groups
  getAccountGroups: (phaseId) => request(`/api/account-groups${phaseId ? `?phase_id=${phaseId}` : ""}`),
  createAccountGroup: (data) => request("/api/account-groups", { method: "POST", body: JSON.stringify(data) }),
  updateAccountGroup: (id, data) => request(`/api/account-groups/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAccountGroup: (id) => request(`/api/account-groups/${id}`, { method: "DELETE" }),
  reorderAccountGroups: (phaseId, orderedIds) => request("/api/account-groups/reorder", { method: "PATCH", body: JSON.stringify({ phase_id: phaseId, ordered_ids: orderedIds }) }),
  moveAccountToGroup: (accountId, groupId) => request(`/api/accounts/${accountId}/move-to-group${groupId !== null ? `?group_id=${groupId}` : ""}`, { method: "PATCH" }),

  // Accounts
  getAccounts: (phaseId) => request(`/api/accounts${phaseId ? `?phase_id=${phaseId}` : ""}`),
  createAccount: (data) => request("/api/accounts", { method: "POST", body: JSON.stringify(data) }),
  updateAccount: (id, data) => request(`/api/accounts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  bulkCreateAccounts: (items) => request("/api/accounts/bulk", { method: "POST", body: JSON.stringify(items) }),
  reorderAccounts: (phaseId, orderedIds) => request("/api/accounts/reorder", { method: "PATCH", body: JSON.stringify({ phase_id: phaseId, ordered_ids: orderedIds }) }),
  deleteAccount: (id) => request(`/api/accounts/${id}`, { method: "DELETE" }),

  // Tasks
  getTasks: (accountId) => request(`/api/tasks${accountId ? `?account_id=${accountId}` : ""}`),
  getTask: (id) => request(`/api/tasks/${id}`),
  createTask: (data) => request("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
  bulkCreateTasks: (items) => request("/api/tasks/bulk", { method: "POST", body: JSON.stringify(items) }),
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

  // Template Checklists
  getTemplateChecklists: (templateId) => request(`/api/template-checklists?template_id=${templateId}`),
  upsertChecklist: (data) => request("/api/template-checklists", { method: "PUT", body: JSON.stringify(data) }),
  bulkUpsertChecklists: (items) => request("/api/template-checklists/bulk", { method: "PUT", body: JSON.stringify(items) }),
  deleteTemplateChecklists: (templateId) => request(`/api/template-checklists?template_id=${templateId}`, { method: "DELETE" }),

  // PBC Items
  getPBCItems: (params) => {
    const sp = new URLSearchParams();
    if (params?.client_id) sp.set("client_id", params.client_id);
    if (params?.account_id) sp.set("account_id", params.account_id);
    const qs = sp.toString();
    return request(`/api/pbc-items${qs ? `?${qs}` : ""}`);
  },
  getPBCItem: (id) => request(`/api/pbc-items/${id}`),
  createPBCItem: (data) => request("/api/pbc-items", { method: "POST", body: JSON.stringify(data) }),
  updatePBCItem: (id, data) => request(`/api/pbc-items/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deletePBCItem: (id) => request(`/api/pbc-items/${id}`, { method: "DELETE" }),
  bulkCreatePBCItems: (items) => request("/api/pbc-items/bulk", { method: "POST", body: JSON.stringify(items) }),
  bulkUpdatePBCItems: (ids, updates) => request("/api/pbc-items/bulk-update", { method: "PATCH", body: JSON.stringify({ ids, updates }) }),
  bulkDeletePBCItems: (ids) => request("/api/pbc-items/bulk-delete", { method: "POST", body: JSON.stringify({ ids }) }),

  // Interviews
  getInterviews: (params) => {
    const sp = new URLSearchParams();
    if (params?.client_id) sp.set("client_id", params.client_id);
    if (params?.account_id) sp.set("account_id", params.account_id);
    return request(`/api/interviews?${sp}`);
  },
  getInterview: (id) => request(`/api/interviews/${id}`),
  createInterview: (data) => request("/api/interviews", { method: "POST", body: JSON.stringify(data) }),
  updateInterview: (id, data) => request(`/api/interviews/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteInterview: (id) => request(`/api/interviews/${id}`, { method: "DELETE" }),
  syncInterviewQuestions: (interviewId, questions) => request(`/api/interview-questions/sync?interview_id=${interviewId}`, { method: "PUT", body: JSON.stringify(questions) }),

  // PBC Excel Items
  getPBCExcelItems: (clientId, fileName) => {
    const sp = new URLSearchParams({ client_id: clientId });
    if (fileName) sp.set("file_name", fileName);
    return request(`/api/pbc-excel-items?${sp}`);
  },
  upsertPBCExcelItem: (data) => request("/api/pbc-excel-items", { method: "PUT", body: JSON.stringify(data) }),
  bulkUpsertPBCExcel: (items) => request("/api/pbc-excel-items/bulk", { method: "PUT", body: JSON.stringify(items) }),

  // Notifications
  getNotifications: () => request("/api/notifications"),

  // Search
  search: (q) => request(`/api/search?q=${encodeURIComponent(q)}`),

  // Dashboard
  getDashboard: () => request("/api/dashboard"),

  // Engagement tree
  getEngagementTree: () => request("/api/engagement-tree"),
};

export default api;
