import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import {
  Gauge, RefreshCw, Plus, Loader2, Star, AlertTriangle, MessageSquareWarning,
  ThumbsUp, Link2, X, BookOpen, Lightbulb, MapPin, TrendingDown,
  Building2, Award, ChevronRight,
} from "lucide-react";

// Командный центр CEO: подключаем точку (2GIS) → тянем отзывы → AI сопоставляет
// жалобы со стандартами → собственник видит пульс, главные боли и ленту.
export default function CommandCenter() {
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null); // point_id | null (вся сеть)
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [showConnect, setShowConnect] = useState(false);
  const [toast, setToast] = useState("");

  async function load(pointId = selected) {
    setError("");
    try {
      const cc = await api.reviews.commandCenter(pointId);
      setData(cc);
    } catch (e) {
      setError(e.message || "Не удалось загрузить командный центр");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(selected); /* eslint-disable-next-line */ }, [selected]);

  async function onSync() {
    const pid = selected || data?.points?.[0]?.id;
    if (!pid) { setShowConnect(true); return; }
    setSyncing(true);
    setToast("");
    try {
      const res = await api.reviews.sync(pid);
      setToast(`Добавлено новых отзывов: ${res.added}, разобрано: ${res.analyzed}`);
      await load(selected);
    } catch (e) {
      setError(e.message || "Не удалось обновить отзывы");
    } finally {
      setSyncing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400">
        <Loader2 size={32} className="animate-spin mb-3" />
        <span>Загружаем командный центр…</span>
      </div>
    );
  }

  const points = data?.points || [];
  const pulse = data?.pulse || {};
  const hasData = pulse.total > 0;

  return (
    <div className="max-w-6xl mx-auto">
      {/* Шапка */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-100 text-brand-600 flex items-center justify-center">
            <Gauge size={22} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Командный центр</h1>
            <p className="text-sm text-slate-500">Что говорят клиенты — и где это бьёт по стандартам.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowConnect(true)} className="btn btn-secondary">
            <Plus size={16} className="mr-1" /> Подключить точку
          </button>
          {points.length > 0 && (
            <button onClick={onSync} disabled={syncing} className="btn btn-primary">
              {syncing
                ? <><Loader2 size={16} className="mr-2 animate-spin" /> Обновляем…</>
                : <><RefreshCw size={16} className="mr-2" /> Обновить отзывы</>}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}
      {toast && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm">
          {toast}
        </div>
      )}

      {/* Переключатель точек */}
      {points.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          <PointChip active={!selected} onClick={() => setSelected(null)}
            label="Вся сеть" sub={`${points.reduce((a, p) => a + p.reviews_count, 0)} отзывов`} />
          {points.map((p) => (
            <PointChip key={p.id} active={selected === p.id} onClick={() => setSelected(p.id)}
              label={p.name} sub={`${p.reviews_count} · ${p.negative_count} негатив`}
              alert={p.negative_count > 0} />
          ))}
        </div>
      )}

      {/* Пустое состояние */}
      {points.length === 0 && !showConnect && (
        <EmptyState onConnect={() => setShowConnect(true)} />
      )}

      {/* Точка есть, но отзывов нет */}
      {points.length > 0 && !hasData && (
        <div className="text-center py-16 text-slate-500 bg-white rounded-2xl border border-slate-200">
          <MessageSquareWarning size={36} className="mx-auto mb-3 text-slate-300" />
          <p className="mb-4">Точка подключена, но отзывов пока нет.</p>
          <button onClick={onSync} disabled={syncing} className="btn btn-primary">
            {syncing ? <><Loader2 size={16} className="mr-2 animate-spin" /> Обновляем…</>
              : <><RefreshCw size={16} className="mr-2" /> Подтянуть отзывы</>}
          </button>
        </div>
      )}

      {hasData && (
        <>
          {!selected && points.length > 1 && (
            <NetworkOverview points={points} onPick={(id) => setSelected(id)} />
          )}
          <PulseRow pulse={pulse} />
          <Problems problems={data.problems || []} />
          <RecentFeed recent={data.recent || []} />
        </>
      )}

      {showConnect && (
        <ConnectModal
          onClose={() => setShowConnect(false)}
          onConnected={async (newId) => {
            setShowConnect(false);
            await load(selected);
            setSelected(newId);
            setToast("Точка подключена. Нажмите «Обновить отзывы», чтобы подтянуть данные.");
          }}
        />
      )}
    </div>
  );
}

function PointChip({ active, onClick, label, sub, alert }) {
  return (
    <button onClick={onClick} className={`px-4 py-2 rounded-xl border text-left transition-colors ${
      active ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-white hover:bg-slate-50"
    }`}>
      <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
        <MapPin size={14} className={active ? "text-brand-600" : "text-slate-400"} />
        {label}
        {alert && <span className="w-1.5 h-1.5 rounded-full bg-red-500" />}
      </div>
      <div className="text-xs text-slate-500 mt-0.5">{sub}</div>
    </button>
  );
}

function NetworkOverview({ points, onPick }) {
  // «Проблемность» точки: жалобы важнее всего, затем доля негатива, затем оценка.
  const score = (p) => {
    const negShare = p.reviews_count ? p.negative_count / p.reviews_count : 0;
    return p.complaints_count * 10 + negShare * 5 - (p.avg_rating || 0);
  };
  const ranked = [...points].sort((a, b) => score(b) - score(a));
  const worst = ranked[0];
  const best = ranked[ranked.length - 1];

  return (
    <div className="mb-8">
      <h2 className="text-lg font-bold text-slate-900 mb-3 flex items-center gap-2">
        <Building2 size={18} className="text-brand-600" /> Сеть точек
      </h2>
      <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
        {ranked.map((p) => {
          const isWorst = p.id === worst.id && p.complaints_count > 0;
          const isBest = p.id === best.id && !isWorst && p.complaints_count === 0;
          return (
            <button key={p.id} onClick={() => onPick(p.id)}
              className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-slate-50 transition-colors">
              <span className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
                isWorst ? "bg-red-100 text-red-600" : isBest ? "bg-green-100 text-green-600" : "bg-slate-100 text-slate-500"
              }`}>
                {isWorst ? <TrendingDown size={18} /> : isBest ? <Award size={18} /> : <MapPin size={18} />}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-900 truncate">{p.name}</span>
                  {isWorst && <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700">Проседает</span>}
                  {isBest && <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700">Лучшая</span>}
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                  <span className="flex items-center gap-1">
                    <Star size={12} className="text-amber-400" fill="currentColor" />
                    {p.avg_rating ? p.avg_rating.toFixed(1) : "—"}
                  </span>
                  <span>{p.reviews_count} отзывов</span>
                  {p.complaints_count > 0 && (
                    <span className="text-red-600 font-medium">{p.complaints_count} {plural(p.complaints_count, "жалоба", "жалобы", "жалоб")}</span>
                  )}
                </div>
              </div>
              {/* мини-бар доли негатива */}
              <div className="hidden sm:block w-28 flex-shrink-0">
                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full bg-red-400 rounded-full"
                    style={{ width: `${p.reviews_count ? Math.round((p.negative_count / p.reviews_count) * 100) : 0}%` }} />
                </div>
                <div className="text-[10px] text-slate-400 mt-1 text-right">
                  {p.reviews_count ? Math.round((p.negative_count / p.reviews_count) * 100) : 0}% негатив
                </div>
              </div>
              <ChevronRight size={18} className="text-slate-300 flex-shrink-0" />
            </button>
          );
        })}
      </div>
    </div>
  );
}

function PulseRow({ pulse }) {
  const cards = [
    { label: "Всего отзывов", value: pulse.total, icon: MessageSquareWarning, tone: "slate" },
    { label: "Средняя оценка", value: pulse.avg_rating ? pulse.avg_rating.toFixed(1) : "—", icon: Star, tone: "amber" },
    { label: "Негатив", value: pulse.negative, icon: TrendingDown, tone: "red" },
    { label: "Жалобы", value: pulse.complaints, icon: AlertTriangle, tone: "orange" },
  ];
  const tones = {
    slate: "bg-slate-100 text-slate-600",
    amber: "bg-amber-100 text-amber-600",
    red: "bg-red-100 text-red-600",
    orange: "bg-orange-100 text-orange-600",
  };
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {cards.map((c) => (
        <div key={c.label} className="bg-white rounded-2xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-500">{c.label}</span>
            <span className={`w-8 h-8 rounded-lg flex items-center justify-center ${tones[c.tone]}`}>
              <c.icon size={16} />
            </span>
          </div>
          <div className="text-3xl font-bold text-slate-900">{c.value}</div>
        </div>
      ))}
    </div>
  );
}

function Problems({ problems }) {
  return (
    <div className="mb-8">
      <h2 className="text-lg font-bold text-slate-900 mb-3 flex items-center gap-2">
        <AlertTriangle size={18} className="text-orange-500" /> Главные боли
      </h2>
      {problems.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-2xl p-6 text-center text-green-700">
          <ThumbsUp size={28} className="mx-auto mb-2" />
          Жалоб не найдено — точка работает штатно.
        </div>
      ) : (
        <div className="space-y-3">
          {problems.map((p, i) => (
            <div key={i} className="bg-white rounded-2xl border border-slate-200 p-5">
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex items-center gap-2 min-w-0">
                  {p.document_id
                    ? <BookOpen size={16} className="text-brand-600 flex-shrink-0" />
                    : <MessageSquareWarning size={16} className="text-slate-400 flex-shrink-0" />}
                  <h3 className="font-semibold text-slate-900 truncate">{p.title}</h3>
                </div>
                <span className="flex-shrink-0 text-xs font-bold px-2.5 py-1 rounded-full bg-red-100 text-red-700">
                  {p.count} {plural(p.count, "жалоба", "жалобы", "жалоб")}
                </span>
              </div>

              {p.recommendation && (
                <div className="flex items-start gap-2 text-sm text-slate-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mb-3">
                  <Lightbulb size={15} className="text-amber-500 mt-0.5 flex-shrink-0" />
                  <span>{p.recommendation}</span>
                </div>
              )}

              {p.document_id && p.standard_quote && (
                <p className="text-xs text-slate-500 mb-3 border-l-2 border-slate-200 pl-3">
                  Стандарт: «{truncate(p.standard_quote, 160)}»
                </p>
              )}

              {p.samples?.length > 0 && (
                <div className="space-y-1.5">
                  {p.samples.map((s, j) => (
                    <p key={j} className="text-sm text-slate-600 flex gap-2">
                      <span className="text-slate-300">“</span>{s}
                    </p>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RecentFeed({ recent }) {
  return (
    <div>
      <h2 className="text-lg font-bold text-slate-900 mb-3">Лента отзывов</h2>
      <div className="space-y-3">
        {recent.map((r) => (
          <div key={r.id} className="bg-white rounded-2xl border border-slate-200 p-4">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900 text-sm">{r.author || "Гость"}</span>
                <Stars n={r.rating} />
              </div>
              <SentimentChip sentiment={r.sentiment} topic={r.topic} />
            </div>
            <p className="text-sm text-slate-700 leading-relaxed">{r.text}</p>
            {r.is_complaint && r.matched_document_title && (
              <div className="mt-2 flex items-center gap-1.5 text-xs text-brand-700">
                <BookOpen size={13} /> Задевает: {r.matched_document_title}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Stars({ n }) {
  if (!n) return null;
  return (
    <span className="flex items-center gap-0.5 text-amber-400">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star key={s} size={12} fill={s <= n ? "currentColor" : "none"}
          className={s <= n ? "" : "text-slate-300"} />
      ))}
    </span>
  );
}

function SentimentChip({ sentiment, topic }) {
  const map = {
    positive: { c: "bg-green-100 text-green-700", t: "Позитив" },
    negative: { c: "bg-red-100 text-red-700", t: "Негатив" },
    neutral: { c: "bg-slate-100 text-slate-600", t: "Нейтрально" },
  };
  const s = map[sentiment] || map.neutral;
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${s.c}`}>
      {topic ? `${topic} · ${s.t}` : s.t}
    </span>
  );
}

function EmptyState({ onConnect }) {
  return (
    <div className="text-center py-16 bg-white rounded-2xl border border-slate-200">
      <div className="w-14 h-14 rounded-2xl bg-brand-100 text-brand-600 flex items-center justify-center mx-auto mb-4">
        <Gauge size={28} />
      </div>
      <h2 className="text-xl font-bold text-slate-900 mb-1">Подключите первую точку</h2>
      <p className="text-slate-500 max-w-md mx-auto mb-6">
        Вставьте ссылку на филиал в 2GIS — система подтянет отзывы клиентов и покажет,
        где реальность расходится с вашими стандартами.
      </p>
      <button onClick={onConnect} className="btn btn-primary">
        <Plus size={16} className="mr-1" /> Подключить точку
      </button>
    </div>
  );
}

function ConnectModal({ onClose, onConnected }) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const p = await api.reviews.connectPoint({ name, url });
      onConnected(p.id);
    } catch (e2) {
      setErr(e2.message || "Не удалось подключить точку");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[60] bg-slate-900/60 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <Link2 size={18} className="text-brand-600" />
            <span className="font-semibold text-slate-900">Подключить точку</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700"><X size={22} /></button>
        </div>
        <form onSubmit={submit} className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Название точки</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required
              placeholder="Зал на Абая"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Ссылка на 2GIS</label>
            <input value={url} onChange={(e) => setUrl(e.target.value)} required
              placeholder="https://2gis.kz/almaty/firm/70000001…"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none" />
            <p className="text-xs text-slate-400 mt-1">Откройте точку в 2GIS и скопируйте ссылку из адресной строки.</p>
          </div>
          {err && <div className="text-sm text-red-600">{err}</div>}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn btn-secondary">Отмена</button>
            <button type="submit" disabled={busy} className="btn btn-primary">
              {busy ? <><Loader2 size={16} className="mr-2 animate-spin" /> Подключаем…</> : "Подключить"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}
function truncate(s, n) { return s && s.length > n ? s.slice(0, n).trim() + "…" : s; }
