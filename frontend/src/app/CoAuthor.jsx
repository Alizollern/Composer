import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { PenLine, Loader2, Lightbulb, FileText, Sparkles, Check, AlertCircle, ChevronRight } from "lucide-react";

// AI-соавтор стандартов: показывает дыры (из реальных вопросов без ответа) и
// генерирует черновик регламента, который владелец проверяет и сохраняет.
export default function CoAuthor() {
  const [sug, setSug] = useState(null);
  const [loadingSug, setLoadingSug] = useState(true);
  const [instruction, setInstruction] = useState("");
  const [drafting, setDrafting] = useState(false);
  const [draft, setDraft] = useState(null); // {title, category, content}
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const navigate = useNavigate();

  async function loadSuggestions() {
    setLoadingSug(true);
    try {
      setSug(await api.coauthor.suggestions());
    } catch (e) {
      // мягко: блок предложений просто не покажем
    } finally {
      setLoadingSug(false);
    }
  }

  useEffect(() => { loadSuggestions(); }, []);

  async function generate() {
    const text = instruction.trim();
    if (!text || drafting) return;
    setError("");
    setSaved(false);
    setDraft(null);
    setDrafting(true);
    try {
      setDraft(await api.coauthor.draft(text));
    } catch (e) {
      setError(e.message || "Не удалось собрать черновик");
    } finally {
      setDrafting(false);
    }
  }

  function useSuggestion(s) {
    const base = `Напиши стандарт: «${s.title}».`;
    const qs = (s.questions || []).length
      ? ` Учти вопросы сотрудников: ${s.questions.join("; ")}.`
      : "";
    setInstruction(base + qs);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function saveDraft() {
    if (!draft) return;
    setError("");
    try {
      await api.documents.create({
        title: draft.title,
        content: draft.content,
        category: draft.category || "",
        publish: false, // сохраняем как ЧЕРНОВИК — владелец публикует осознанно
      });
      setSaved(true);
    } catch (e) {
      setError(e.message || "Не удалось сохранить черновик");
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Шапка */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-brand-100 text-brand-600 flex items-center justify-center">
          <PenLine size={22} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Соавтор стандартов</h1>
          <p className="text-sm text-slate-500">Подскажет, чего не хватает, и напишет черновик регламента.</p>
        </div>
      </div>

      {/* Генератор черновика */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 mb-6">
        <label className="text-sm font-semibold text-slate-900 flex items-center gap-2 mb-2">
          <Sparkles size={16} className="text-brand-500" /> Опишите, про что стандарт
        </label>
        <textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={3}
          placeholder="Напр.: Напиши регламент по заморозке абонементов: минимум 7 дней, максимум 14, за день до начала."
          className="w-full resize-none border border-slate-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-brand-400"
        />
        <div className="flex justify-end mt-3">
          <button onClick={generate} disabled={drafting || !instruction.trim()}
            className="btn btn-primary !rounded-xl flex items-center gap-2 disabled:opacity-50">
            {drafting ? <Loader2 size={16} className="animate-spin" /> : <PenLine size={16} />}
            Сгенерировать черновик
          </button>
        </div>
      </div>

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm mb-6 flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Черновик */}
      {draft && (
        <div className="bg-white rounded-2xl border border-brand-200 p-5 mb-6">
          <div className="text-xs font-semibold text-brand-600 uppercase tracking-wide mb-3">
            Черновик — проверьте перед сохранением
          </div>
          <input
            value={draft.title}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            className="w-full text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 mb-2 outline-none focus:border-brand-400"
          />
          <input
            value={draft.category}
            onChange={(e) => setDraft({ ...draft, category: e.target.value })}
            placeholder="Категория (кому адресован)"
            className="w-full text-sm text-slate-500 mb-3 outline-none"
          />
          <textarea
            value={draft.content}
            onChange={(e) => setDraft({ ...draft, content: e.target.value })}
            rows={14}
            className="w-full resize-y border border-slate-200 rounded-xl px-3 py-2.5 text-sm leading-relaxed outline-none focus:border-brand-400 font-mono"
          />
          <div className="flex items-center justify-between mt-3">
            {saved ? (
              <span className="text-sm text-green-600 flex items-center gap-1">
                <Check size={16} /> Сохранено как черновик в Базе знаний
              </span>
            ) : <span />}
            <div className="flex gap-2">
              {saved && (
                <button onClick={() => navigate("/app/knowledge")}
                  className="btn btn-secondary !rounded-xl">Открыть в Базе знаний</button>
              )}
              <button onClick={saveDraft} disabled={saved}
                className="btn btn-primary !rounded-xl flex items-center gap-2 disabled:opacity-50">
                <FileText size={16} /> Сохранить как черновик
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Предложения из пробелов */}
      <div>
        <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
          <Lightbulb size={16} className="text-amber-500" /> Чего не хватает в стандартах
        </h2>
        {loadingSug ? (
          <div className="flex items-center gap-2 text-slate-500 text-sm">
            <Loader2 size={16} className="animate-spin" /> Анализирую вопросы без ответа…
          </div>
        ) : !sug?.has_gaps ? (
          <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-sm text-green-700">
            Пробелов не найдено — на все вопросы сотрудников в базе есть ответ.
          </div>
        ) : (
          <>
            <p className="text-xs text-slate-500 mb-3">
              Основано на {sug.count} реальных вопросах, на которые бот не нашёл ответа.
            </p>
            <div className="space-y-2">
              {sug.suggestions.map((s, i) => (
                <button key={i} onClick={() => useSuggestion(s)}
                  className="w-full text-left bg-white rounded-xl border border-slate-200 px-4 py-3 hover:border-brand-400 hover:bg-brand-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-900">{s.title}</span>
                    <ChevronRight size={16} className="text-slate-300" />
                  </div>
                  {s.rationale && <p className="text-xs text-slate-500 mt-1">{s.rationale}</p>}
                  {s.questions?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {s.questions.map((q, j) => (
                        <span key={j} className="text-xs bg-slate-100 text-slate-600 rounded-md px-2 py-0.5">
                          «{q}»
                        </span>
                      ))}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
