// Тонкий клиент к локальному API. Тот же origin (в dev — прокси Vite).
const base = "";

async function j(path, opts) {
  const r = await fetch(base + path, opts);
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.json();
}

export const api = {
  health: () => j("/api/health"),

  // компании
  companies: () => j("/api/companies"),
  createCompany: (name, profile) =>
    j("/api/companies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, profile }),
    }),
  company: (slug) => j(`/api/companies/${encodeURIComponent(slug)}`),
  saveProfile: (slug, content) =>
    j(`/api/companies/${encodeURIComponent(slug)}/profile`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    }),
  companyFile: (slug, name) =>
    j(`/api/companies/${encodeURIComponent(slug)}/files/${encodeURIComponent(name)}`),

  // прогоны
  run: (goal, company) =>
    j("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal, mode: "dynamic", company }),
    }),
  runStatus: (id) => j(`/api/run/${id}`),
  runs: () => j("/api/runs"),
  streamUrl: (id) => `${base}/api/run/${id}/stream`,

  // диалог
  agents: () => j("/api/agents"),
  chat: (agent, message, session_id) =>
    j("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent, message, session_id }),
    }),
};
