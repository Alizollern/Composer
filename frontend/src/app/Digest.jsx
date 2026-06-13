import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Bell, AlertTriangle, AlertOctagon, Loader2, RefreshCw, Star, TrendingUp, ChevronRight, FileText } from "lucide-react";

// Сводка собственнику: продукт сам докладывает, где болит. Цифры считаются на
// бэке детерминированно, текст — короткий брифинг поверх них.
export default function Digest() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await api.digest.get());
    } catch (e) {
      setError(e.message || "Не удалось собрать сводку");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-slate-500 text-sm">
        <Loader2 size={18} className="animate-spin" /> Собираю сводку по сети…
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
        {error}
      </div>
    );
  }

  const pulse = data?.pulse || {};
  const alerts = data?.alerts || [];
  const points = data?.points || [];
  const problems = data?.top_problems || [];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Шапка */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-100 text-brand-600 flex items-center justify-center">
            <Bell size={22} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Сводка по сети</h1>
            <p className="text-sm text-slate-500">Что важно знать собственнику прямо сейчас.</p>
          </div>
        </div>
        <button onClick={load} className="btn btn-secondary !rounded-xl flex items-center gap-2">
          <RefreshCw size={16} /> Обновить
        </button>
      </div>

      {!data?.has_data ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center">
          <p className="text-slate-600">{data?.summary}</p>
          <button onClick={() => navigate("/app/command-center")}
            className="btn btn-primary !rounded-xl mt-4">
            Открыть Командный центр
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Брифинг */}
          <div className="bg-gradient-to-br from-brand-50 to-white rounded-2xl border border-brand-100 p-5">
            <div className="text-xs font-semibold text-brand-600 uppercase tracking-wide mb-2">
              Брифинг опер-дира
            </div>
            <p className="text-slate-800 leading-relaxed">{data.summary}</p>
          </div>

          {/* Пульс сети */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Stat label="Отзывов" value={pulse.total} />
            <Stat label="Средний рейтинг" value={pulse.avg_rating} icon={<Star size={14} className="text-amber-400" />} />
            <Stat label="Негативных" value={pulse.negative} tone={pulse.negative > 0 ? "bad" : "ok"} />
            <Stat label="Жалоб" value={pulse.complaints} tone={pulse.complaints > 0 ? "bad" : "ok"} />
          </div>

          {/* Тревоги */}
          <div>
            <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
              <AlertTriangle size={16} className="text-amber-500" />
              Тревоги {alerts.length > 0 && <span className="text-slate-400">({alerts.length})</span>}
            </h2>
            {alerts.length === 0 ? (
              <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-sm text-green-700">
                Острых тревог нет — сеть работает ровно.
              </div>
            ) : (
              <div className="space-y-2">
                {alerts.map((a, i) => <AlertCard key={i} alert={a} onOpen={() => navigate("/app/command-center")} />)}
              </div>
            )}
          </div>

          {/* Точки: от худшей к лучшей */}
          {points.length > 1 && (
            <div>
              <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <TrendingUp size={16} className="text-brand-500" /> Точки — от проблемных к лучшим
              </h2>
              <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100">
                {points.map((p, i) => (
                  <button key={p.id} onClick={() => navigate("/app/command-center")}
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors text-left">
                    <div className="flex items-center gap-3">
                      <span className={`w-6 h-6 rounded-md text-xs font-bold flex items-center justify-center ${
                        i === 0 ? "bg-red-100 text-red-600" : i === points.length - 1 ? "bg-green-100 text-green-600" : "bg-slate-100 text-slate-500"
                      }`}>{i + 1}</span>
                      <div>
                        <div className="text-sm font-medium text-slate-900">{p.name}</div>
                        <div className="text-xs text-slate-500">
                          {p.reviews_count} отзывов · {p.complaints_count} жалоб · негатив {p.negative_count}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-slate-700 flex items-center gap-1">
                        <Star size={13} className="text-amber-400" /> {p.avg_rating || "—"}
                      </span>
                      <ChevronRight size={16} className="text-slate-300" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Главные боли сети */}
          {problems.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <FileText size={16} className="text-slate-500" /> Главные боли клиентов
              </h2>
              <div className="space-y-2">
                {problems.map((pr, i) => (
                  <div key={i} className="bg-white rounded-xl border border-slate-200 px-4 py-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-900">{pr.title}</span>
                      <span className="text-xs text-slate-500">{pr.count} жалоб</span>
                    </div>
                    {pr.recommendation && (
                      <p className="text-xs text-slate-600 mt-1">→ {pr.recommendation}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, icon, tone }) {
  const color = tone === "bad" ? "text-red-600" : tone === "ok" ? "text-green-600" : "text-slate-900";
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <div className="text-xs text-slate-500 mb-1 flex items-center gap-1">{icon}{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value ?? 0}</div>
    </div>
  );
}

function AlertCard({ alert, onOpen }) {
  const high = alert.severity === "high";
  return (
    <button onClick={onOpen}
      className={`w-full flex items-start gap-3 px-4 py-3 rounded-xl border text-left transition-colors ${
        high ? "bg-red-50 border-red-200 hover:bg-red-100" : "bg-amber-50 border-amber-200 hover:bg-amber-100"
      }`}>
      <span className={`mt-0.5 ${high ? "text-red-600" : "text-amber-600"}`}>
        {high ? <AlertOctagon size={18} /> : <AlertTriangle size={18} />}
      </span>
      <span className={`text-sm ${high ? "text-red-800" : "text-amber-800"}`}>{alert.message}</span>
    </button>
  );
}
