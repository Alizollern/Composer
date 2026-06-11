import { useRef, useState } from "react";
import { Sparkles, Check, Loader2, FileText, ArrowRight, CircleDot } from "lucide-react";
import { api } from "../lib/api.js";
import { renderMd } from "../lib/md.js";
import { roleLabel, toolLabel, toolDetail } from "../lib/labels.js";

const SUGGESTIONS = [
  "Подготовь стандарты сервиса для нашей кофейни",
  "Сделай анализ конкурентов в нашем сегменте",
  "Составь план запуска новой точки",
  "Напиши обращение к команде о целях квартала",
];

export default function CommandCenter({ company, companyName, onProduced, onOpenDocs }) {
  const [goal, setGoal] = useState("");
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState([]);
  const [phase, setPhase] = useState("");
  const [result, setResult] = useState("");
  const [docs, setDocs] = useState([]);
  const [started, setStarted] = useState(false);
  const srcRef = useRef(null);
  const seenRef = useRef(new Set());

  const greet = (() => {
    const h = new Date().getHours();
    return h < 6 ? "Доброй ночи" : h < 12 ? "Доброе утро" : h < 18 ? "Добрый день" : "Добрый вечер";
  })();

  function pushStep(s) { setSteps((prev) => [...prev, s]); }

  function handleEvent(d) {
    switch (d.type) {
      case "start": pushStep({ kind: "spark", label: "Анализирую задачу и распределяю работу" }); break;
      case "subagent_start": {
        const key = d.agent + ":" + (d.depth || 0);
        if (seenRef.current.has(key)) break;
        seenRef.current.add(key);
        pushStep({ kind: "run", label: roleLabel(d.agent), detail: d.task || "" });
        break;
      }
      case "subagent_done": pushStep({ kind: "done", label: roleLabel(d.agent) + " — готово" }); break;
      case "tool_call":
        if (d.name && d.name.startsWith("delegate_to_")) break;
        pushStep({ kind: "tool", label: toolLabel(d.name), detail: toolDetail(d.input) });
        break;
      case "text":
        if (d.text && d.text.trim().length > 12 && d.text.trim().length < 600)
          pushStep({ kind: "note", label: d.text.trim() });
        break;
      case "done": pushStep({ kind: "done", label: "Работа завершена" }); setPhase("готово"); break;
      default: break;
    }
  }

  async function finalize(runId) {
    setRunning(false);
    setPhase("готово");
    try {
      const run = await api.runStatus(runId);
      if (run.status === "error") { setResult(""); setPhase("ошибка"); return; }
      const res = run.results || {};
      setResult(res.final || "");
      setDocs(res.new_files && res.new_files.length ? res.new_files : Object.keys(res.files || {}));
      onProduced && onProduced();
    } catch { /* ignore */ }
  }

  async function run() {
    const g = goal.trim();
    if (!g || running) return;
    if (srcRef.current) { srcRef.current.close(); srcRef.current = null; }
    seenRef.current = new Set();
    setRunning(true); setStarted(true); setSteps([]); setResult(""); setDocs([]); setPhase("идёт обработка");

    let runId;
    try {
      const r = await api.run(g, company || null);
      runId = r.run_id;
    } catch (e) {
      pushStep({ kind: "err", label: "Не удалось запустить", detail: String(e) });
      setRunning(false); setPhase("ошибка"); return;
    }
    pushStep({ kind: "accept", label: "Двойник принял задачу" });

    const src = new EventSource(api.streamUrl(runId));
    srcRef.current = src;
    src.onmessage = (ev) => {
      let d; try { d = JSON.parse(ev.data); } catch { return; }
      handleEvent(d);
      if (d.type === "end" || d.type === "done") {
        src.close(); if (srcRef.current === src) srcRef.current = null;
        finalize(runId);
      }
    };
    src.onerror = () => { src.close(); if (srcRef.current === src) srcRef.current = null; finalize(runId); };
  }

  return (
    <div>
      {/* Заголовок */}
      <div className="mb-7">
        <div className="eyebrow">Командный центр{companyName ? ` · ${companyName}` : ""}</div>
        <h1 className="mt-2 text-3xl sm:text-4xl font-semibold text-ink">{greet}. Чем займёмся?</h1>
        <p className="mt-2 text-ink-soft">
          Опишите задачу обычными словами — двойник возьмёт её на себя{companyName ? ` для «${companyName}»` : ""}.
        </p>
      </div>

      {/* Поле задачи */}
      <div className="rounded-3xl border border-line bg-white p-4 shadow-soft focus-within:border-emerald/40 focus-within:ring-4 focus-within:ring-emerald/10 transition-all">
        <textarea
          rows={3}
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") run(); }}
          placeholder="Например: подготовь стандарты сервиса и адаптируй под нашу сеть"
          className="w-full resize-none bg-transparent px-2 py-1 text-[16px] leading-relaxed text-ink outline-none placeholder:text-ink-muted/70"
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setGoal(s)}
                className="rounded-full border border-line px-3 py-1.5 text-[12.5px] text-ink-soft transition-colors hover:border-emerald/40 hover:bg-emerald/5 hover:text-emerald-600"
              >
                {s}
              </button>
            ))}
          </div>
          <button className="btn btn-primary btn-sm whitespace-nowrap" disabled={running} onClick={run}>
            {running ? <><Loader2 size={16} className="animate-spin" /> Двойник работает…</> : <>Поручить двойнику <ArrowRight size={16} /></>}
          </button>
        </div>
      </div>

      {/* Сессия */}
      {started && (
        <div className="mt-7 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]">
          {/* Лента работы */}
          <div className="rounded-3xl border border-line bg-white p-5 shadow-soft">
            <div className="mb-4 flex items-center justify-between">
              <span className="text-sm font-semibold text-ink">Двойник за работой</span>
              <span
                className={
                  "rounded-full px-2.5 py-1 text-[11px] font-medium " +
                  (running ? "bg-emerald/10 text-emerald-600" : phase === "ошибка" ? "bg-red-50 text-red-500" : "bg-paper-deep text-ink-muted")
                }
              >
                {phase}
              </span>
            </div>
            <div className="space-y-3">
              {steps.map((s, i) => <StepRow key={i} s={s} />)}
              {steps.length === 0 && <div className="text-sm text-ink-muted">Готовлюсь…</div>}
            </div>
          </div>

          {/* Результат */}
          <div className="flex flex-col rounded-3xl border border-line bg-white p-6 shadow-soft">
            <span className="mb-4 text-sm font-semibold text-ink">Результат</span>
            <div className="flex-1">
              {result
                ? <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(result) }} />
                : (
                  <div className="flex h-full min-h-[140px] items-center justify-center rounded-2xl bg-paper/60 text-center text-sm text-ink-muted">
                    {running ? (
                      <span className="inline-flex items-center gap-2"><Loader2 size={15} className="animate-spin" /> Двойник работает над задачей…</span>
                    ) : "Готовый материал появится здесь."}
                  </div>
                )}
            </div>
            {docs.length > 0 && (
              <div className="mt-5 flex flex-wrap gap-2 border-t border-line pt-4">
                {docs.map((f) => (
                  <button
                    key={f}
                    onClick={onOpenDocs}
                    className="inline-flex items-center gap-1.5 rounded-full bg-emerald/10 px-3 py-1.5 text-[13px] font-medium text-emerald-600 transition-colors hover:bg-emerald/15"
                  >
                    <FileText size={13} /> {f}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* Одна строка ленты */
function StepRow({ s }) {
  if (s.kind === "note") {
    return (
      <div className="rounded-xl border-l-2 border-emerald/40 bg-paper/60 px-3 py-2 text-[13.5px] italic text-ink-soft">
        {s.label}
      </div>
    );
  }
  const ICON = {
    spark: <Sparkles size={13} />,
    accept: <CircleDot size={13} />,
    run: <Loader2 size={13} className="animate-spin" />,
    tool: <span className="h-1.5 w-1.5 rounded-full bg-current" />,
    done: <Check size={13} />,
    err: <span className="font-bold">!</span>,
  }[s.kind] || <span className="h-1.5 w-1.5 rounded-full bg-current" />;

  const tone =
    s.kind === "done" ? "bg-emerald text-white"
    : s.kind === "err" ? "bg-red-100 text-red-500"
    : s.kind === "tool" ? "bg-paper-deep text-ink-muted"
    : "bg-emerald/12 text-emerald-600";

  return (
    <div className="flex items-start gap-3">
      <span className={"mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full " + tone}>{ICON}</span>
      <div className="min-w-0 flex-1">
        <div className="text-[14px] text-ink">{s.label}</div>
        {s.detail && <div className="truncate text-[12.5px] text-ink-muted">{s.detail}</div>}
      </div>
    </div>
  );
}
