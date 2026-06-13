import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { CheckSquare, Loader2, Plus, Circle, Clock, CheckCircle2, Trash2, MapPin, AlertCircle } from "lucide-react";

// Отслеживание исправлений: петля «нашли → поручили → проверили».
// Задачи приходят из тревог/болей или создаются вручную; статус ведём здесь.
const STATUS_META = {
  open: { label: "Открыта", icon: Circle, cls: "text-slate-400", next: "in_progress", nextLabel: "В работу" },
  in_progress: { label: "В работе", icon: Clock, cls: "text-amber-500", next: "done", nextLabel: "Закрыть" },
  done: { label: "Сделана", icon: CheckCircle2, cls: "text-green-600", next: "open", nextLabel: "Вернуть" },
};
const SOURCE_LABEL = { manual: "Вручную", alert: "Из тревоги", problem: "Боль клиентов", gap: "Пробел" };

export default function Actions() {
  const [data, setData] = useState({ items: [], counts: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState(""); // "", open, in_progress, done
  const [newTitle, setNewTitle] = useState("");
  const [adding, setAdding] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await api.actions.list(filter));
    } catch (e) {
      setError(e.message || "Не удалось загрузить задачи");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filter]);

  async function add() {
    const title = newTitle.trim();
    if (!title || adding) return;
    setAdding(true);
    try {
      await api.actions.create({ title, source: "manual" });
      setNewTitle("");
      load();
    } catch (e) {
      setError(e.message || "Не удалось создать задачу");
    } finally {
      setAdding(false);
    }
  }

  async function setStatus(id, status) {
    try {
      await api.actions.setStatus(id, status);
      load();
    } catch (e) { setError(e.message); }
  }

  async function remove(id) {
    try {
      await api.actions.remove(id);
      load();
    } catch (e) { setError(e.message); }
  }

  const counts = data.counts || {};
  const FILTERS = [
    { key: "", label: `Все${counts.total ? ` (${counts.total})` : ""}` },
    { key: "open", label: `Открытые${counts.open ? ` (${counts.open})` : ""}` },
    { key: "in_progress", label: `В работе${counts.in_progress ? ` (${counts.in_progress})` : ""}` },
    { key: "done", label: `Сделанные${counts.done ? ` (${counts.done})` : ""}` },
  ];

  return (
    <div className="max-w-3xl mx-auto">
      {/* Шапка */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-brand-100 text-brand-600 flex items-center justify-center">
          <CheckSquare size={22} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Исправления</h1>
          <p className="text-sm text-slate-500">Поручения по точкам: нашли проблему → поручили → проверили.</p>
        </div>
      </div>

      {/* Добавить задачу */}
      <div className="flex gap-2 mb-4">
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") add(); }}
          placeholder="Что нужно исправить? Напр.: протирать тренажёры каждые 2 часа на Сатпаева"
          className="flex-1 border border-slate-200 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-brand-400"
        />
        <button onClick={add} disabled={adding || !newTitle.trim()}
          className="btn btn-primary !rounded-xl flex items-center gap-2 disabled:opacity-50">
          {adding ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />} Поручить
        </button>
      </div>

      {/* Фильтры */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {FILTERS.map((f) => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className={`text-sm px-3 py-1.5 rounded-lg border transition-colors ${
              filter === f.key ? "bg-brand-600 text-white border-brand-600" : "bg-white text-slate-600 border-slate-200 hover:border-brand-300"
            }`}>
            {f.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm mb-4 flex items-center gap-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Список */}
      {loading ? (
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <Loader2 size={16} className="animate-spin" /> Загружаю задачи…
        </div>
      ) : data.items.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500 text-sm">
          Задач нет. Создайте поручение выше или приходите из «Сводки» — там у тревог есть кнопка «Поручить».
        </div>
      ) : (
        <div className="space-y-2">
          {data.items.map((it) => {
            const meta = STATUS_META[it.status] || STATUS_META.open;
            const Icon = meta.icon;
            return (
              <div key={it.id} className={`bg-white rounded-xl border border-slate-200 p-4 ${it.status === "done" ? "opacity-70" : ""}`}>
                <div className="flex items-start gap-3">
                  <Icon size={18} className={`${meta.cls} mt-0.5 flex-shrink-0`} />
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm font-medium text-slate-900 ${it.status === "done" ? "line-through" : ""}`}>
                      {it.title}
                    </div>
                    {it.detail && <p className="text-xs text-slate-500 mt-1">{it.detail}</p>}
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      <span className={`text-xs px-2 py-0.5 rounded-md bg-slate-100 ${meta.cls}`}>{meta.label}</span>
                      {it.point_name && (
                        <span className="text-xs px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 flex items-center gap-1">
                          <MapPin size={11} /> {it.point_name}
                        </span>
                      )}
                      <span className="text-xs text-slate-400">{SOURCE_LABEL[it.source] || it.source}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={() => setStatus(it.id, meta.next)}
                      className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 hover:border-brand-400 hover:bg-brand-50 text-slate-700 transition-colors">
                      {meta.nextLabel}
                    </button>
                    <button onClick={() => remove(it.id)}
                      className="text-slate-300 hover:text-red-500 p-1.5 transition-colors" title="Удалить">
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
