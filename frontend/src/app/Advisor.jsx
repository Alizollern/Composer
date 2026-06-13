import React, { useState, useRef, useEffect } from "react";
import { api } from "../lib/api";
import { Sparkles, Send, Loader2, User, Lightbulb, Search, Network, AlertTriangle, FileSearch, Check } from "lucide-react";

// Цифровой опер-дир: владелец задаёт свободный вопрос — агент сам ходит в данные
// компании (отзывы, точки, стандарты, пробелы) и собирает деловой ответ.
// Стрим «мыслей»: пока агент думает, видно вживую, какие инструменты он зовёт.
const EXAMPLES = [
  "Какая точка проседает и что делать в первую очередь?",
  "На что больше всего жалуются клиенты в сети?",
  "Чего не хватает в наших стандартах?",
  "Как дела в сети в целом — есть ли проблемы?",
];

// Понятные ярлыки для инструментов агента (название → что показать человеку).
const TOOL_LABELS = {
  search_standards: { label: "Читаю стандарты", icon: Search },
  network_overview: { label: "Смотрю всю сеть точек", icon: Network },
  point_problems: { label: "Изучаю жалобы точки", icon: AlertTriangle },
  list_gaps: { label: "Проверяю пробелы в знаниях", icon: FileSearch },
};

function toolStep(name) {
  return TOOL_LABELS[name] || { label: name, icon: Sparkles };
}

export default function Advisor() {
  const [messages, setMessages] = useState([]); // {role:"user"|"assistant", text}
  const [steps, setSteps] = useState([]); // живые шаги текущего раздумья: {name,label,icon,done}
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, steps, busy]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setError("");
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setSteps([]);
    setBusy(true);

    let answered = false;
    try {
      await api.advisor.askStream(q, (ev) => {
        if (ev.type === "tool_call") {
          const st = toolStep(ev.name);
          setSteps((s) => [...s, { name: ev.name, label: st.label, icon: st.icon, done: false }]);
        } else if (ev.type === "tool_result") {
          // помечаем последний незавершённый шаг с этим именем как выполненный
          setSteps((s) => {
            const copy = [...s];
            for (let i = copy.length - 1; i >= 0; i--) {
              if (copy[i].name === ev.name && !copy[i].done) { copy[i] = { ...copy[i], done: true }; break; }
            }
            return copy;
          });
        } else if (ev.type === "final") {
          answered = true;
          setMessages((m) => [...m, { role: "assistant", text: ev.answer || "Нет ответа." }]);
          setSteps([]);
        } else if (ev.type === "error") {
          setError(ev.message || "Опер-дир временно недоступен");
          setSteps([]);
        }
      });
      if (!answered && !error) {
        // поток закрылся без финала — мягкая подсказка
        setMessages((m) => [...m, { role: "assistant", text: "Не удалось собрать ответ. Попробуйте переформулировать вопрос." }]);
      }
    } catch (e) {
      setError(e.message || "Опер-дир временно недоступен");
    } finally {
      setBusy(false);
      setSteps([]);
    }
  }

  return (
    <div className="max-w-3xl mx-auto flex flex-col h-full">
      {/* Шапка */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-brand-100 text-brand-600 flex items-center justify-center">
          <Sparkles size={22} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Цифровой опер-дир</h1>
          <p className="text-sm text-slate-500">Спросите по сети — он сам поднимет отзывы, точки и стандарты.</p>
        </div>
      </div>

      {/* Диалог */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <div className="flex items-center gap-2 text-slate-900 font-semibold mb-3">
              <Lightbulb size={18} className="text-amber-500" /> С чего начать
            </div>
            <div className="grid sm:grid-cols-2 gap-2">
              {EXAMPLES.map((ex) => (
                <button key={ex} onClick={() => send(ex)}
                  className="text-left text-sm text-slate-700 border border-slate-200 rounded-xl px-3 py-2.5 hover:border-brand-400 hover:bg-brand-50 transition-colors">
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} text={m.text} />
        ))}

        {/* Живые «мысли» агента: какие инструменты он сейчас зовёт */}
        {busy && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-brand-100 text-brand-600">
              <Sparkles size={16} />
            </div>
            <div className="rounded-2xl px-4 py-3 bg-white border border-slate-200 max-w-[85%] w-full">
              {steps.length === 0 ? (
                <div className="flex items-center gap-2 text-slate-500 text-sm">
                  <Loader2 size={16} className="animate-spin" />
                  Опер-дир изучает данные сети…
                </div>
              ) : (
                <div className="space-y-2">
                  {steps.map((st, i) => {
                    const Icon = st.icon;
                    return (
                      <div key={i} className="flex items-center gap-2 text-sm">
                        <span className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 ${
                          st.done ? "bg-green-100 text-green-600" : "bg-brand-100 text-brand-600"
                        }`}>
                          {st.done ? <Check size={13} /> : <Icon size={13} />}
                        </span>
                        <span className={st.done ? "text-slate-500" : "text-slate-800"}>{st.label}</span>
                        {!st.done && <Loader2 size={13} className="animate-spin text-slate-400" />}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Ввод */}
      <form onSubmit={(e) => { e.preventDefault(); send(); }}
        className="sticky bottom-0 bg-slate-50 pt-2">
        <div className="flex items-end gap-2 bg-white border border-slate-200 rounded-2xl p-2 shadow-sm">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            rows={1}
            placeholder="Спросите опер-дира о вашей сети…"
            className="flex-1 resize-none max-h-32 px-3 py-2 outline-none text-sm bg-transparent"
          />
          <button type="submit" disabled={busy || !input.trim()}
            className="btn btn-primary !rounded-xl flex-shrink-0 disabled:opacity-50">
            {busy ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
        <p className="text-xs text-slate-400 text-center mt-2">
          Опер-дир отвечает по данным вашей компании. Проверяйте важные решения.
        </p>
      </form>
    </div>
  );
}

function Bubble({ role, text }) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
        isUser ? "bg-slate-200 text-slate-600" : "bg-brand-100 text-brand-600"
      }`}>
        {isUser ? <User size={16} /> : <Sparkles size={16} />}
      </div>
      <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap max-w-[85%] ${
        isUser ? "bg-brand-600 text-white" : "bg-white border border-slate-200 text-slate-800"
      }`}>
        {text}
      </div>
    </div>
  );
}
