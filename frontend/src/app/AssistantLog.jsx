import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "./AuthProvider";
import { api } from "../lib/api";
import {
  Search, Bot, CheckCircle2, Ban, Boxes, RefreshCw, ScrollText, ShieldCheck,
} from "lucide-react";

// Человеческое описание каждого типа события журнала.
function describe(rec) {
  switch (rec.kind) {
    case "chat.retrieval": {
      const cands = (rec.candidates || [])
        .map((c) => `${c.title} (${c.score})`)
        .join(", ");
      return {
        icon: Search,
        tone: "slate",
        title: `Поиск по базе знаний — лучшее совпадение ${rec.best_score} (порог ${rec.min_score})`,
        detail: cands ? `Кандидаты: ${cands}` : "Подходящих документов не найдено",
      };
    }
    case "chat.decision": {
      const answered = rec.decision === "answered";
      return {
        icon: answered ? CheckCircle2 : Ban,
        tone: answered ? "green" : "amber",
        title: answered
          ? "Ассистент ответил по стандартам"
          : "Ассистент честно отказал (не выдумал)",
        detail: `Рубеж: ${rec.gate === "retrieval" ? "поиск" : "генерация"}` +
          (rec.sources && rec.sources.length ? ` · источники: ${rec.sources.join(", ")}` : ""),
      };
    }
    case "llm.complete": {
      const op = rec.operation === "chat_strict_rag" ? "ответ чат-бота"
        : rec.operation === "quiz_generate" ? "генерация теста"
        : rec.operation || "запрос";
      return {
        icon: Bot,
        tone: "brand",
        title: `Обращение к модели (${op}) · ${rec.elapsed_ms ?? "?"} мс`,
        detail: rec.output ? `Ответ: ${rec.output}` : (rec.error ? `Ошибка: ${rec.error}` : ""),
      };
    }
    case "agent.run":
    case "agent.orchestrate":
      return {
        icon: Boxes,
        tone: "brand",
        title: `Агент ${rec.agent || rec.orchestrator || "оркестратор"} · ${rec.elapsed_ms ?? "?"} мс`,
        detail: rec.output || rec.error || "",
      };
    default:
      return { icon: ScrollText, tone: "slate", title: rec.kind, detail: "" };
  }
}

const TONES = {
  slate: "bg-slate-50 text-slate-600 border-slate-200",
  green: "bg-green-50 text-green-700 border-green-200",
  amber: "bg-amber-50 text-amber-700 border-amber-200",
  brand: "bg-brand-50 text-brand-600 border-brand-200",
};

function fmtTime(ts) {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleString("ru-RU", {
      day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch {
    return ts;
  }
}

export default function AssistantLog() {
  const { user } = useAuth();
  const isOwner = user?.role === "owner";

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [auto, setAuto] = useState(false);
  const [error, setError] = useState("");

  const fetchLog = useCallback(async () => {
    try {
      const data = await api.agentLog.list(200);
      setRows(data);
      setError("");
    } catch (e) {
      setError(e.message || "Не удалось загрузить журнал");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOwner) fetchLog();
  }, [isOwner, fetchLog]);

  // Авто-обновление каждые 4 секунды, когда включено наблюдение.
  useEffect(() => {
    if (!auto || !isOwner) return;
    const id = setInterval(fetchLog, 4000);
    return () => clearInterval(id);
  }, [auto, isOwner, fetchLog]);

  if (!isOwner) {
    return (
      <div className="max-w-2xl mx-auto bg-white rounded-lg border border-slate-200 p-12 text-center">
        <ShieldCheck size={40} className="text-slate-300 mx-auto mb-4" />
        <h2 className="text-lg font-bold text-slate-900 mb-1">Доступ только для владельца</h2>
        <p className="text-slate-500">Журнал ассистента виден владельцу компании.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 space-y-3 md:space-y-0">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Журнал ассистента</h1>
          <p className="text-slate-500 mt-1">
            Каждое решение ИИ: что нашёл в базе, на чём ответил и почему отказал.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-sm text-slate-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={auto}
              onChange={(e) => setAuto(e.target.checked)}
              className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            <span>Наблюдать вживую</span>
          </label>
          <button onClick={fetchLog} className="btn btn-secondary">
            <RefreshCw size={16} className={`mr-2 ${loading ? "animate-spin" : ""}`} />
            Обновить
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-100">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-lg p-4 h-16 border border-slate-200 animate-pulse" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <div className="bg-white rounded-lg border border-slate-200 border-dashed p-12 text-center">
          <ScrollText size={40} className="text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-slate-900 mb-1">Журнал пуст</h3>
          <p className="text-slate-500">
            Задайте ассистенту вопрос — и здесь появится каждый его шаг.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {rows.map((rec, i) => {
            const d = describe(rec);
            const Icon = d.icon;
            return (
              <div
                key={i}
                className="bg-white rounded-lg border border-slate-200 p-4 flex items-start space-x-3"
              >
                <div className={`flex-shrink-0 p-2 rounded-md border ${TONES[d.tone] || TONES.slate}`}>
                  <Icon size={16} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-900">{d.title}</p>
                    <span className="text-xs text-slate-400 flex-shrink-0 ml-3">{fmtTime(rec.ts)}</span>
                  </div>
                  {d.detail && (
                    <p className="text-sm text-slate-500 mt-0.5 break-words">{d.detail}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
