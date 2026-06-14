import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { Swords, Loader2, RefreshCw, Star, TrendingUp, TrendingDown, Trophy, ThumbsUp, Target, MapPin, Search } from "lucide-react";

// Конкуренты: где мы проигрываем соседям, а где лидируем. Цифры (рейтинги)
// сравниваются детерминированно — модель не нужна, экран всегда наполнен.
export default function Competitors() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await api.competitors.get());
    } catch (e) {
      setError(e.message || "Не удалось собрать сравнение");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function syncPoint(pointId) {
    setSyncing(pointId);
    try {
      await api.competitors.sync(pointId);
      await load();
    } catch (e) {
      setError(e.message || "Не удалось найти конкурентов");
    } finally {
      setSyncing("");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-slate-500 text-sm">
        <Loader2 size={18} className="animate-spin" /> Сравниваю с конкурентами…
      </div>
    );
  }

  const points = data?.points || [];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Шапка */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-100 text-brand-600 flex items-center justify-center">
            <Swords size={22} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Конкуренты</h1>
            <p className="text-sm text-slate-500">Кто рядом, чем лучше и где у нас преимущество.</p>
          </div>
        </div>
        <button onClick={load} className="btn btn-secondary !rounded-xl flex items-center gap-2">
          <RefreshCw size={16} /> Обновить
        </button>
      </div>

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm mb-4">
          {error}
        </div>
      )}

      {/* Брифинг */}
      {data?.summary && (
        <div className="bg-gradient-to-br from-brand-50 to-white rounded-2xl border border-brand-100 p-5 mb-5">
          <div className="text-xs font-semibold text-brand-600 uppercase tracking-wide mb-2">
            Разведка рынка
          </div>
          <p className="text-slate-800 leading-relaxed">{data.summary}</p>
        </div>
      )}

      {points.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
          Нет подключённых точек. Сначала подключите точку в «Командном центре».
        </div>
      ) : (
        <div className="space-y-4">
          {points.map((p) => (
            <PointCard key={p.point_id} p={p} onSync={syncPoint} syncing={syncing === p.point_id} />
          ))}
        </div>
      )}
    </div>
  );
}

const STATUS_META = {
  behind: { label: "Проигрываем", cls: "bg-red-100 text-red-700", icon: TrendingDown },
  close: { label: "Отстаём", cls: "bg-amber-100 text-amber-700", icon: TrendingDown },
  leading: { label: "Лидируем", cls: "bg-green-100 text-green-700", icon: Trophy },
  unknown: { label: "Нет данных", cls: "bg-slate-100 text-slate-500", icon: TrendingUp },
};

function PointCard({ p, onSync, syncing }) {
  const meta = STATUS_META[p.status] || STATUS_META.unknown;
  const Icon = meta.icon;
  const empty = p.competitors_count === 0;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5">
      {/* Заголовок точки */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="text-base font-semibold text-slate-900">{p.point_name}</div>
          {!empty && (
            <div className="flex items-center gap-3 mt-1 text-sm">
              <span className="flex items-center gap-1 text-slate-700">
                <Star size={13} className="text-amber-400" /> {p.my_rating || "—"}
                <span className="text-slate-400">мы</span>
              </span>
              <span className="text-slate-300">vs</span>
              <span className="flex items-center gap-1 text-slate-700">
                <Star size={13} className="text-amber-400" /> {p.best_competitor_rating || "—"}
                <span className="text-slate-400">лучший рядом</span>
              </span>
            </div>
          )}
        </div>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1 flex-shrink-0 ${meta.cls}`}>
          <Icon size={13} /> {meta.label}
        </span>
      </div>

      {empty ? (
        <div className="flex items-center justify-between gap-3 bg-slate-50 rounded-xl px-4 py-3">
          <span className="text-sm text-slate-500">Конкуренты ещё не найдены.</span>
          <button onClick={() => onSync(p.point_id)} disabled={syncing}
            className="btn btn-primary !rounded-xl flex items-center gap-2 disabled:opacity-50">
            {syncing ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />} Найти конкурентов
          </button>
        </div>
      ) : (
        <>
          <p className="text-sm text-slate-600 mb-3">{p.verdict} Обходим {p.ahead_of} из {p.competitors_count}.</p>

          {/* Зоны роста / преимущества */}
          <div className="grid sm:grid-cols-2 gap-3 mb-4">
            {p.opportunities?.length > 0 && (
              <div className="rounded-xl border border-amber-100 bg-amber-50/50 p-3">
                <div className="text-xs font-semibold text-amber-700 flex items-center gap-1 mb-1.5">
                  <Target size={13} /> Где соседи сильнее (догнать)
                </div>
                <ul className="space-y-1">
                  {p.opportunities.map((o, i) => (
                    <li key={i} className="text-sm text-slate-700">• {o}</li>
                  ))}
                </ul>
              </div>
            )}
            {p.advantages?.length > 0 && (
              <div className="rounded-xl border border-green-100 bg-green-50/50 p-3">
                <div className="text-xs font-semibold text-green-700 flex items-center gap-1 mb-1.5">
                  <ThumbsUp size={13} /> Их слабости (наш козырь)
                </div>
                <ul className="space-y-1">
                  {p.advantages.map((a, i) => (
                    <li key={i} className="text-sm text-slate-700">• {a}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Список конкурентов */}
          <div className="divide-y divide-slate-100 border-t border-slate-100">
            {p.competitors.map((c) => (
              <div key={c.id} className="py-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-900">{c.name}</div>
                  <div className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                    {c.distance_m > 0 && (
                      <span className="flex items-center gap-1"><MapPin size={11} /> {c.distance_m} м</span>
                    )}
                    <span>{c.reviews_count} отзывов</span>
                  </div>
                  {c.strengths?.length > 0 && (
                    <div className="text-xs text-slate-500 mt-1">
                      Хвалят: {c.strengths.join(", ")}
                    </div>
                  )}
                </div>
                <span className="text-sm font-semibold text-slate-700 flex items-center gap-1 flex-shrink-0">
                  <Star size={13} className="text-amber-400" /> {c.rating || "—"}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-3">
            <button onClick={() => onSync(p.point_id)} disabled={syncing}
              className="text-xs flex items-center gap-1 text-slate-500 hover:text-brand-600 transition-colors">
              {syncing ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />} Обновить конкурентов
            </button>
          </div>
        </>
      )}
    </div>
  );
}
