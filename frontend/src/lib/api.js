// Тонкий клиент к локальному API (Evergreen)
// В dev-режиме проксируется Vite, в проде отдается тем же сервером, поэтому base = ""
const base = "";

// Ключ для хранения токена
const TOKEN_KEY = "evergreen_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

/**
 * Базовый fetcher с подкидыванием токена и обработкой 401
 */
async function j(path, opts = {}) {
  const headers = new Headers(opts.headers || {});
  
  const token = getToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Если это не FormData, ставим application/json
  if (!(opts.body instanceof FormData) && !headers.has("Content-Type") && opts.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(base + path, { ...opts, headers });

  if (response.status === 401) {
    clearToken();
    window.dispatchEvent(new Event("auth:unauthorized"));
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    const errText = await response.text();
    let errMsg = response.statusText;
    try {
      const errJson = JSON.parse(errText);
      errMsg = errJson.detail || errJson.message || errMsg;
    } catch (e) {
      errMsg = errText || errMsg;
    }
    throw new Error(errMsg);
  }

  // Для эндпоинтов, возвращающих файл (download)
  if (opts.responseType === "blob") {
    return response.blob();
  }

  // 204 No Content (например, удаление) — тела нет, JSON парсить нечего.
  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const api = {
  health: () => j("/api/health"),

  // --- Auth ---
  auth: {
    registerCompany: (data) => j("/api/auth/register-company", { method: "POST", body: JSON.stringify(data) }),
    login: (data) => j("/api/auth/login", { method: "POST", body: JSON.stringify(data) }),
    me: () => j("/api/auth/me"),
  },

  // --- Users ---
  users: {
    create: (data) => j("/api/users", { method: "POST", body: JSON.stringify(data) }),
    list: () => j("/api/users"),
  },

  // --- Documents (Knowledge Base) ---
  documents: {
    list: (status_filter) => {
      const qs = status_filter ? `?status_filter=${status_filter}` : "";
      return j(`/api/documents${qs}`);
    },
    get: (id) => j(`/api/documents/${id}`),
    getContent: (id) => j(`/api/documents/${id}/content`),
    create: (data) => j("/api/documents", { method: "POST", body: JSON.stringify(data) }),
    upload: (file, category) => {
      const formData = new FormData();
      formData.append("file", file);
      if (category) formData.append("category", category);
      return j("/api/documents/upload", { method: "POST", body: formData });
    },
    updateAudience: (id, data) => j(`/api/documents/${id}/audience`, { method: "POST", body: JSON.stringify(data) }),
    updateStatus: (id, status) => j(`/api/documents/${id}/status`, { method: "POST", body: JSON.stringify({ status }) }),
    addVersion: (id, content) => j(`/api/documents/${id}/versions`, { method: "POST", body: JSON.stringify({ content }) }),
    downloadOriginal: (id) => j(`/api/documents/${id}/original`, { responseType: "blob" }),
  },

  // --- Chat ---
  chat: {
    ask: (question) => j("/api/chat", { method: "POST", body: JSON.stringify({ question }) }),
  },

  // --- Gaps ---
  gaps: {
    list: () => j("/api/gaps"),
  },

  // --- Agent log (журнал «мыслей» ассистента, только владелец) ---
  agentLog: {
    list: (limit = 200) => j(`/api/agent-log?limit=${limit}`),
  },

  // --- Quiz ---
  quiz: {
    generate: (id, num_questions = 5) => j(`/api/documents/${id}/quiz`, { method: "POST", body: JSON.stringify({ num_questions }) }),
    grade: (quiz_token, answers) => j("/api/quiz/grade", { method: "POST", body: JSON.stringify({ quiz_token, answers }) }),
  },

  // --- Tracks (Onboarding) ---
  tracks: {
    create: (data) => j("/api/tracks", { method: "POST", body: JSON.stringify(data) }),
    autoBuild: (data = {}) => j("/api/tracks/auto", { method: "POST", body: JSON.stringify(data) }),
    list: () => j("/api/tracks"),
    get: (id) => j(`/api/tracks/${id}`),
    addStep: (id, data) => j(`/api/tracks/${id}/steps`, { method: "POST", body: JSON.stringify(data) }),
    deleteStep: (id, stepId) => j(`/api/tracks/${id}/steps/${stepId}`, { method: "DELETE" }),
    updateStatus: (id, status) => j(`/api/tracks/${id}/status`, { method: "POST", body: JSON.stringify({ status }) }),
    enroll: (id, user_id) => j(`/api/tracks/${id}/enroll`, { method: "POST", body: JSON.stringify({ user_id }) }),
    enrollMe: (id) => j(`/api/tracks/${id}/enroll-me`, { method: "POST" }),
    myEnrollments: () => j("/api/my/enrollments"),
    submitStep: (enrollment_id, step_id, data) => j(`/api/enrollments/${enrollment_id}/steps/${step_id}/submit`, { method: "POST", body: JSON.stringify(data) }),
    progress: (id) => j(`/api/tracks/${id}/progress`),
  },

  // --- Командный центр (отзывы → инсайты, «цифровой опер-дир») ---
  reviews: {
    connectPoint: (data) => j("/api/points", { method: "POST", body: JSON.stringify(data) }),
    sync: (point_id) => j(`/api/points/${point_id}/sync`, { method: "POST" }),
    commandCenter: (point_id) => {
      const qs = point_id ? `?point_id=${point_id}` : "";
      return j(`/api/command-center${qs}`);
    },
  },

  // --- Сводка и тревоги собственнику ---
  digest: {
    get: () => j("/api/digest"),
  },

  // --- Цифровой опер-дир (агент с инструментами) ---
  advisor: {
    ask: (question) => j("/api/advisor", { method: "POST", body: JSON.stringify({ question }) }),
    // Стрим «мыслей»: onEvent({type,...}) вызывается на каждое событие агента
    // (text, tool_call, tool_result, final, error). Возвращает промис, который
    // резолвится по завершению потока.
    askStream: async (question, onEvent) => {
      const headers = new Headers({ "Content-Type": "application/json" });
      const token = getToken();
      if (token) headers.set("Authorization", `Bearer ${token}`);

      const resp = await fetch(base + "/api/advisor/stream", {
        method: "POST",
        headers,
        body: JSON.stringify({ question }),
      });

      if (resp.status === 401) {
        clearToken();
        window.dispatchEvent(new Event("auth:unauthorized"));
        throw new Error("Unauthorized");
      }
      if (!resp.ok || !resp.body) {
        const txt = await resp.text().catch(() => "");
        throw new Error(txt || resp.statusText || "Опер-дир недоступен");
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // SSE-кадры разделены пустой строкой "\n\n"
        let sep;
        while ((sep = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          const line = frame.trim();
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          try {
            onEvent(JSON.parse(payload));
          } catch (e) {
            // битый кадр — пропускаем, поток продолжается
          }
        }
      }
    },
  },
};
