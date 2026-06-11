import { useEffect, useRef, useState } from "react";
import { Send, Loader2 } from "lucide-react";
import { api } from "../lib/api.js";
import { renderMd } from "../lib/md.js";

export default function Chat() {
  const [agent, setAgent] = useState(null);
  const [session, setSession] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef(null);

  useEffect(() => {
    api.agents().then((list) => {
      const names = list.map((a) => a.name);
      const pref = ["advisor", "writer", "analyst", "orchestrator"];
      setAgent(pref.find((p) => names.includes(p)) || names[0] || "advisor");
    }).catch(() => setAgent("advisor"));
  }, []);

  useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [msgs, busy]);

  async function send() {
    const m = text.trim();
    if (!m || busy) return;
    setText("");
    setMsgs((p) => [...p, { role: "user", text: m }]);
    setBusy(true);
    try {
      const res = await api.chat(agent, m, session);
      setSession(res.session_id);
      setMsgs((p) => [...p, { role: "twin", text: res.reply || "…" }]);
    } catch {
      setMsgs((p) => [...p, { role: "twin", text: "Связь прервалась. Попробуйте ещё раз." }]);
    } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <div className="eyebrow">Диалог</div>
        <h1 className="mt-2 text-3xl sm:text-4xl font-semibold text-ink">Поговорите с двойником</h1>
        <p className="mt-2 text-ink-soft">Быстрые вопросы, идеи, советы. Двойник держит контекст беседы.</p>
      </div>

      <div className="flex h-[62vh] flex-col overflow-hidden rounded-3xl border border-line bg-white shadow-soft">
        <div ref={logRef} className="flex-1 space-y-4 overflow-y-auto p-5">
          {msgs.length === 0 && (
            <div className="flex h-full items-center justify-center px-6 text-center text-sm text-ink-muted">
              Задайте первый вопрос — например, «как поднять средний чек на точке?»
            </div>
          )}
          {msgs.map((m, i) => (
            <div key={i} className={"flex " + (m.role === "user" ? "justify-end" : "justify-start")}>
              <div
                className={
                  "max-w-[82%] rounded-2xl px-4 py-2.5 text-[15px] " +
                  (m.role === "user"
                    ? "bg-emerald text-white rounded-br-md"
                    : "bg-paper border border-line text-ink rounded-bl-md")
                }
              >
                {m.role === "twin"
                  ? <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(m.text) }} />
                  : m.text}
              </div>
            </div>
          ))}
          {busy && (
            <div className="flex justify-start">
              <div className="inline-flex items-center gap-2 rounded-2xl rounded-bl-md border border-line bg-paper px-4 py-2.5 text-sm text-ink-muted">
                <Loader2 size={14} className="animate-spin" /> Двойник думает…
              </div>
            </div>
          )}
        </div>

        <div className="flex items-end gap-2 border-t border-line p-3">
          <textarea
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Сообщение двойнику…"
            className="max-h-32 flex-1 resize-none rounded-2xl border border-line bg-paper px-4 py-3 text-[15px] text-ink outline-none transition-all placeholder:text-ink-muted/70 focus:border-emerald focus:ring-4 focus:ring-emerald/10"
          />
          <button className="btn btn-primary grid h-11 w-11 place-items-center !px-0" disabled={busy} onClick={send} aria-label="Отправить">
            <Send size={17} />
          </button>
        </div>
      </div>
    </div>
  );
}
