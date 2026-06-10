import { useRef, useState } from "react";
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
      case "start": pushStep({ ico: "✦", label: "Анализирую задачу и распределяю работу" }); break;
      case "subagent_start": {
        const key = d.agent + ":" + (d.depth || 0);
        if (seenRef.current.has(key)) break;
        seenRef.current.add(key);
        pushStep({ ico: "▶", label: roleLabel(d.agent), detail: d.task || "" });
        break;
      }
      case "subagent_done": pushStep({ ico: "✓", cls: "done", label: roleLabel(d.agent) + " — готово" }); break;
      case "tool_call":
        if (d.name && d.name.startsWith("delegate_to_")) break;
        pushStep({ ico: "•", cls: "tool", label: toolLabel(d.name), detail: toolDetail(d.input) });
        break;
      case "text":
        if (d.text && d.text.trim().length > 12 && d.text.trim().length < 600)
          pushStep({ ico: "›", cls: "note", note: true, label: d.text.trim() });
        break;
      case "done": pushStep({ ico: "✓", cls: "done", label: "Работа завершена" }); setPhase("готово"); break;
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
      pushStep({ ico: "!", label: "Не удалось запустить", detail: String(e) });
      setRunning(false); setPhase("ошибка"); return;
    }
    pushStep({ ico: "◆", label: "Двойник принял задачу" });

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
      <div className="app-head">
        <div className="eyebrow">Командный центр{companyName ? ` · ${companyName}` : ""}</div>
        <h1 className="serif">{greet}. Чем займёмся?</h1>
        <p>Опишите задачу обычными словами — двойник возьмёт её на себя{companyName ? ` для «${companyName}»` : ""}.</p>
      </div>

      <div className="taskbox">
        <textarea rows={3} value={goal} onChange={(e) => setGoal(e.target.value)}
          onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") run(); }}
          placeholder="Например: подготовь стандарты сервиса и адаптируй под нашу сеть" />
        <div className="taskbox-bar">
          <div className="chips">
            {SUGGESTIONS.map((s) => <button key={s} className="chip" onClick={() => setGoal(s)}>{s}</button>)}
          </div>
          <button className="btn btn-primary" disabled={running} onClick={run}>
            {running ? "Двойник работает…" : "Поручить двойнику →"}
          </button>
        </div>
      </div>

      {started && (
        <div className="session">
          <div className="session-grid">
            <div className="panel">
              <div className="panel-head">
                <span className="panel-title">Двойник за работой</span>
                <span className={"phase-badge" + (running ? "" : " done")}>{phase}</span>
              </div>
              <div className="timeline">
                {steps.map((s, i) => (
                  <div className="tl-item" key={i}>
                    <div className={"tl-ico " + (s.cls || "")}>{s.ico}</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      {s.note ? <div className="tl-note">{s.label}</div>
                        : <><div className="tl-label">{s.label}</div>{s.detail && <div className="tl-detail">{s.detail}</div>}</>}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="panel-head"><span className="panel-title">Результат</span></div>
              <div className="result-body">
                {result
                  ? <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(result) }} />
                  : <div className="placeholder">{running ? "Двойник работает над задачей…" : "Готовый материал появится здесь."}</div>}
              </div>
              {docs.length > 0 && (
                <div className="docs-strip">
                  {docs.map((f) => <button key={f} className="doc-pill" onClick={onOpenDocs}>{f}</button>)}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
