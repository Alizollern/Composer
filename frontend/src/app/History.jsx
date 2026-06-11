import { useEffect, useState } from "react";
import { RefreshCw, X } from "lucide-react";
import { api } from "../lib/api.js";
import { renderMd } from "../lib/md.js";
import { statusLabel } from "../lib/labels.js";

const STATUS_TONE = {
  done: "bg-emerald/10 text-emerald-600",
  error: "bg-red-50 text-red-500",
  running: "bg-amber-50 text-amber-600",
};

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
      <div className="mb-6 flex items-end justify-between">
        <div>
          <div className="eyebrow">История</div>
          <h1 className="mt-2 text-3xl sm:text-4xl font-semibold text-ink">Прошлые поручения</h1>
          <p className="mt-2 text-ink-soft">Журнал задач и их результатов.</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}><RefreshCw size={15} /> Обновить</button>
      </div>

      {runs === null ? (
        <div className="rounded-3xl border border-dashed border-line p-10 text-center text-ink-muted">Загрузка…</div>
      ) : runs.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-line p-10 text-center text-ink-muted">История пуста.</div>
      ) : (
        <div className="space-y-2.5">
          {runs.map((r) => (
            <button
              key={r.id}
              onClick={() => open(r.id)}
              className="flex w-full items-center justify-between gap-4 rounded-2xl border border-line bg-white px-5 py-4 text-left shadow-soft transition-all hover:-translate-y-0.5 hover:border-emerald/30 hover:shadow-lift"
            >
              <div className="min-w-0">
                <div className="truncate text-[15px] font-medium text-ink">{(r.goal || "Без названия").slice(0, 110)}</div>
                <div className="mt-0.5 text-[12.5px] text-ink-muted">
                  {r.created ? new Date(r.created * 1000).toLocaleString("ru-RU") : ""}
                </div>
              </div>
              <span className={"shrink-0 rounded-full px-2.5 py-1 text-[12px] font-medium " + (STATUS_TONE[r.status] || "bg-paper-deep text-ink-muted")}>
                {statusLabel(r.status)}
              </span>
            </button>
          ))}
        </div>
      )}

      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-forest-900/40 p-4 backdrop-blur-sm" onClick={() => setDetail(null)}>
          <div
            className="max-h-[84vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white p-7 shadow-lift"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <h3 className="font-serif text-2xl font-semibold text-ink">{detail.goal}</h3>
              <button className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-ink-muted hover:bg-paper-deep" onClick={() => setDetail(null)}>
                <X size={18} />
              </button>
            </div>
            <div className={"mt-2 inline-block rounded-full px-2.5 py-1 text-[12px] font-medium " + (STATUS_TONE[detail.status] || "bg-paper-deep text-ink-muted")}>
              {statusLabel(detail.status)}
            </div>
            <div className="mt-5">
              {detail.results?.final
                ? <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(detail.results.final) }} />
                : <div className="rounded-2xl bg-paper/60 p-6 text-center text-sm text-ink-muted">{detail.error || "Нет итогового материала."}</div>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
