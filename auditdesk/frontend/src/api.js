const BASE = "http://localhost:8000/api";

async function req(method, path, body) {
  const opts = {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

const get  = (path)        => req("GET",    path);
const post = (path, body)  => req("POST",   path, body);
const put  = (path, body)  => req("PUT",    path, body);
const del  = (path)        => req("DELETE", path);

export const api = {
  // Fiscal Years
  getFYs:      ()       => get("/fiscal-years"),
  createFY:    (body)   => post("/fiscal-years", body),
  updateFY:    (id, b)  => put(`/fiscal-years/${id}`, b),
  deleteFY:    (id)     => del(`/fiscal-years/${id}`),

  // Clients
  getClients:  (fyId)   => get(`/clients?fy_id=${fyId}`),
  createClient:(body)   => post("/clients", body),
  updateClient:(id, b)  => put(`/clients/${id}`, b),
  deleteClient:(id)     => del(`/clients/${id}`),

  // Engagements
  getEngagements: (clientId) => get(`/engagements?client_id=${clientId}`),
  createEngagement: (body)   => post("/engagements", body),
  updateEngagement: (id, b)  => put(`/engagements/${id}`, b),
  deleteEngagement: (id)     => del(`/engagements/${id}`),

  // Phases
  createPhase: (body)  => post("/phases", body),
  updatePhase: (id, b) => put(`/phases/${id}`, b),
  deletePhase: (id)    => del(`/phases/${id}`),

  // Accounts
  getAccounts:      (phaseId) => get(`/accounts?phase_id=${phaseId}`),
  createAccount:    (body)    => post("/accounts", body),
  bulkAccounts:     (body)    => post("/accounts/bulk", body),
  reorderAccounts:  (body)    => put("/accounts/reorder", body),
  updateAccount:    (id, b)   => put(`/accounts/${id}`, b),
  deleteAccount:    (id)      => del(`/accounts/${id}`),

  // Tasks
  getTasks:    (accountId) => get(`/tasks?account_id=${accountId}`),
  createTask:  (body)      => post("/tasks", body),
  updateTask:  (id, b)     => put(`/tasks/${id}`, b),
  deleteTask:  (id)        => del(`/tasks/${id}`),

  // PBC
  getPbc:      (accountId) => get(`/pbc?account_id=${accountId}`),
  createPbc:   (body)      => post("/pbc", body),
  updatePbc:   (id, b)     => put(`/pbc/${id}`, b),
  deletePbc:   (id)        => del(`/pbc/${id}`),

  // Interviews
  getInterviews:   (accountId) => get(`/interviews?account_id=${accountId}`),
  createInterview: (body)      => post("/interviews", body),
  updateInterview: (id, b)     => put(`/interviews/${id}`, b),
  deleteInterview: (id)        => del(`/interviews/${id}`),

  // ICFR
  getIcfr:    (clientId) => get(`/icfr?client_id=${clientId}`),
  getAllIcfr:  ()         => get("/icfr"),
  createIcfr: (body)     => post("/icfr", body),
  updateIcfr: (id, b)    => put(`/icfr/${id}`, b),
  deleteIcfr: (id)       => del(`/icfr/${id}`),

  // Templates
  getTemplates:   ()       => get("/templates"),
  createTemplate: (body)   => post("/templates", body),
  updateTemplate: (id, b)  => put(`/templates/${id}`, b),
  deleteTemplate: (id)     => del(`/templates/${id}`),

  // Settings
  getSettings:    ()      => get("/settings"),
  updateSettings: (body)  => put("/settings", body),

  // Tree
  getTree: () => get("/engagement-tree"),
};
