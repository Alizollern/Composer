import { useEffect, useRef, useState } from "react";
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
    <div>
      <div className="app-head">
        <div className="eyebrow">Диалог</div>
        <h1 className="serif">Поговорите с двойником</h1>
        <p>Быстрые вопросы, идеи, советы. Двойник держит контекст беседы.</p>
      </div>

      <div className="chat">
        <div className="chat-log" ref={logRef}>
          {msgs.length === 0 && <div className="chat-empty">Задайте первый вопрос — например, «как поднять средний чек на точке?»</div>}
          {msgs.map((m, i) => (
            <div key={i} className={"bubble " + m.role}>
              {m.role === "twin"
                ? <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(m.text) }} />
                : m.text}
            </div>
          ))}
          {busy && <div className="bubble twin thinking">Двойник думает…</div>}
        </div>
        <div className="chat-input">
          <textarea rows={1} value={text} onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Сообщение двойнику…" />
          <button className="btn btn-primary" disabled={busy} onClick={send}>→</button>
        </div>
      </div>
    </div>
  );
}
