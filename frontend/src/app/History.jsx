import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { renderMd } from "../lib/md.js";
import { statusLabel } from "../lib/labels.js";

export default function History() {
  const [runs, setRuns] = useState(null);
  const [detail, setDetail] = useState(null);

  async function load() {
    try { const { runs } = await api.runs(); setRuns(runs); }
    catch { setRuns([]); }
  }
  useEffect(() => { load(); }, []);

  async function open(id) {
    try { const run = await api.runStatus(id); setDetail(run); }
    catch { /* ignore */ }
  }

  return (
    <div>
      <div className="app-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <div className="eyebrow">История</div>
          <h1 className="serif">Прошлые поручения</h1>
          <p>Журнал задач и их результатов.</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}>Обновить</button>
      </div>

      {runs === null ? <div className="empty-note">Загрузка…</div>
        : runs.length === 0 ? <div className="empty-note">История пуста.</div>
        : <div className="history-list">
            {runs.map((r) => (
              <div className="run-card" key={r.id} onClick={() => open(r.id)}>
                <div>
                  <div className="run-goal">{(r.goal || "Без названия").slice(0, 110)}</div>
                  <div className="run-meta">{r.created ? new Date(r.created * 1000).toLocaleString("ru-RU") : ""}</div>
                </div>
                <div className={"run-status " + (r.status || "")}>{statusLabel(r.status)}</div>
              </div>
            ))}
          </div>}

      {detail && (
        <div className="modal-back" onClick={() => setDetail(null)}>
          <div className="modal" style={{ maxWidth: 760, maxHeight: "82vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
              <h3 className="serif" style={{ marginBottom: 6 }}>{detail.goal}</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setDetail(null)}>Закрыть</button>
            </div>
            <div className="run-meta" style={{ marginBottom: 18 }}>{statusLabel(detail.status)}</div>
            {detail.results?.final
              ? <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(detail.results.final) }} />
              : <div className="placeholder">{detail.error || "Нет итогового материала."}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
