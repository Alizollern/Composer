import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "./AuthProvider";
import { api } from "../lib/api";
import LessonPlayer from "./LessonPlayer";
import {
  GraduationCap, Sparkles, Trophy, PlayCircle, CheckCircle2, Lock,
  Trash2, Send, Users, BarChart3, Loader2, BookOpen, ChevronDown, ChevronRight,
} from "lucide-react";

export default function Learning() {
  const { user } = useAuth();
  const isManager = user?.role === "owner" || user?.role === "manager";
  return isManager ? <ManagerLearning /> : <EmployeeLearning />;
}

/* ============================ СОТРУДНИК ============================ */

function EmployeeLearning() {
  const [enrollments, setEnrollments] = useState([]);
  const [available, setAvailable] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [active, setActive] = useState(null); // {enrollment, step}

  const load = useCallback(async () => {
    try {
      const [mine, all] = await Promise.all([
        api.tracks.myEnrollments(),
        api.tracks.list(),
      ]);
      setEnrollments(mine);
      const enrolledIds = new Set(mine.map((e) => e.track.id));
      setAvailable(all.filter((t) => !enrolledIds.has(t.id)));
      setError("");
    } catch (e) {
      setError(e.message || "Не удалось загрузить обучение");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const start = async (trackId) => {
    try { await api.tracks.enrollMe(trackId); await load(); }
    catch (e) { setError(e.message); }
  };

  // Текущий шаг = первый непройденный.
  const currentStep = (enr) => enr.steps.find((s) => s.progress.status !== "passed") || null;

  if (loading) return <Loading />;

  return (
    <div className="max-w-3xl mx-auto">
      <Header
        icon={GraduationCap}
        title="Моё обучение"
        subtitle="Короткие карточки по стандартам компании. Свайпай и проходи мини-тесты."
      />
      {error && <ErrorBox text={error} />}

      {enrollments.length === 0 && available.length === 0 && (
        <Empty
          icon={GraduationCap}
          title="Пока нет курсов"
          text="Когда руководитель назначит обучение, оно появится здесь."
        />
      )}

      {enrollments.map((enr) => {
        const total = enr.steps.length;
        const passed = enr.steps.filter((s) => s.progress.status === "passed").length;
        const cur = currentStep(enr);
        const done = enr.status === "completed";
        return (
          <div key={enr.enrollment_id} className="bg-white rounded-xl border border-slate-200 p-5 mb-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900">{enr.track.title}</h3>
                {enr.track.description && (
                  <p className="text-sm text-slate-500 mt-0.5">{enr.track.description}</p>
                )}
              </div>
              {done && (
                <span className="flex items-center gap-1 text-green-700 bg-green-50 border border-green-200 text-xs font-semibold px-2.5 py-1 rounded-full">
                  <Trophy size={13} /> Завершён
                </span>
              )}
            </div>

            <ProgressBar passed={passed} total={total} />

            <div className="mt-4 space-y-1.5">
              {enr.steps.map((s, i) => {
                const st = s.progress.status;
                const isCurrent = cur && cur.id === s.id;
                return (
                  <div key={s.id} className="flex items-center gap-3 text-sm">
                    {st === "passed"
                      ? <CheckCircle2 size={18} className="text-green-600 flex-shrink-0" />
                      : isCurrent
                        ? <PlayCircle size={18} className="text-brand-600 flex-shrink-0" />
                        : <Lock size={16} className="text-slate-300 flex-shrink-0" />}
                    <span className={st === "passed" ? "text-slate-500 line-through" : "text-slate-800"}>
                      {i + 1}. {s.title}
                    </span>
                  </div>
                );
              })}
            </div>

            {cur && (
              <button
                onClick={() => setActive({ enrollment: enr, step: cur })}
                className="btn btn-primary mt-4"
              >
                <PlayCircle size={16} className="mr-2" />
                {passed === 0 ? "Начать обучение" : "Продолжить"}
              </button>
            )}
          </div>
        );
      })}

      {available.length > 0 && (
        <>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mt-8 mb-3">
            Доступные курсы
          </h2>
          {available.map((t) => (
            <div key={t.id} className="bg-white rounded-xl border border-slate-200 p-5 mb-3 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900">{t.title}</h3>
                {t.description && <p className="text-sm text-slate-500 mt-0.5">{t.description}</p>}
              </div>
              <button onClick={() => start(t.id)} className="btn btn-secondary">Начать</button>
            </div>
          ))}
        </>
      )}

      {active && (
        <LessonPlayer
          enrollment={active.enrollment}
          step={active.step}
          onClose={() => setActive(null)}
          onCompleted={async () => { setActive(null); await load(); }}
        />
      )}
    </div>
  );
}

/* ============================ РУКОВОДИТЕЛЬ ============================ */

function ManagerLearning() {
  const [tracks, setTracks] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState(null);

  const load = useCallback(async () => {
    try {
      const [t, u] = await Promise.all([api.tracks.list(), api.users.list()]);
      setTracks(t);
      setUsers(u);
      setError("");
    } catch (e) {
      setError(e.message || "Не удалось загрузить");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const build = async () => {
    setBuilding(true);
    setError("");
    try {
      const track = await api.tracks.autoBuild();
      await load();
      setOpenId(track.id);
    } catch (e) {
      setError(e.message || "Не удалось собрать курс");
    } finally {
      setBuilding(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-3">
        <Header
          icon={GraduationCap}
          title="Обучение"
          subtitle="Собирайте курсы из стандартов и назначайте сотрудникам."
          tight
        />
        <button onClick={build} disabled={building} className="btn btn-primary self-start">
          {building
            ? <><Loader2 size={16} className="mr-2 animate-spin" /> Собираю…</>
            : <><Sparkles size={16} className="mr-2" /> Собрать онбординг из стандартов</>}
        </button>
      </div>

      {error && <ErrorBox text={error} />}

      {tracks.length === 0 ? (
        <Empty
          icon={GraduationCap}
          title="Курсов пока нет"
          text="Нажмите «Собрать онбординг из стандартов» — система сделает курс из всех опубликованных регламентов одним кликом."
        />
      ) : (
        tracks.map((t) => (
          <TrackAdminCard
            key={t.id}
            track={t}
            users={users}
            open={openId === t.id}
            onToggle={() => setOpenId(openId === t.id ? null : t.id)}
            onChange={load}
          />
        ))
      )}
    </div>
  );
}

function TrackAdminCard({ track, users, open, onToggle, onChange }) {
  const [detail, setDetail] = useState(null);
  const [progress, setProgress] = useState([]);
  const [assignee, setAssignee] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const isDraft = track.status === "draft";

  const loadDetail = useCallback(async () => {
    const [d, p] = await Promise.all([
      api.tracks.get(track.id),
      api.tracks.progress(track.id).catch(() => []),
    ]);
    setDetail(d);
    setProgress(p);
  }, [track.id]);

  useEffect(() => { if (open) loadDetail(); }, [open, loadDetail]);

  const deleteStep = async (stepId) => {
    setBusy(true);
    try { await api.tracks.deleteStep(track.id, stepId); await loadDetail(); }
    finally { setBusy(false); }
  };

  const publish = async () => {
    setBusy(true);
    try { await api.tracks.updateStatus(track.id, "published"); await onChange(); }
    finally { setBusy(false); }
  };

  const assign = async () => {
    if (!assignee) return;
    setBusy(true); setMsg("");
    try {
      await api.tracks.enroll(track.id, assignee);
      setMsg("Назначено ✓");
      setAssignee("");
      await loadDetail();
    } catch (e) {
      setMsg(e.message || "Не удалось назначить");
    } finally { setBusy(false); }
  };

  const userName = (id) => {
    const u = users.find((x) => x.id === id);
    return u ? (u.full_name || u.email) : id.slice(0, 8);
  };
  // Назначать имеет смысл сотрудникам; но пусть выбор будет из всех, кроме owner.
  const assignable = users.filter((u) => u.role !== "owner");

  return (
    <div className="bg-white rounded-xl border border-slate-200 mb-3 overflow-hidden">
      <button onClick={onToggle} className="w-full flex items-center justify-between px-5 py-4 text-left">
        <div className="flex items-center gap-3 min-w-0">
          {open ? <ChevronDown size={18} className="text-slate-400" /> : <ChevronRight size={18} className="text-slate-400" />}
          <span className="font-bold text-slate-900 truncate">{track.title}</span>
          <StatusBadge status={track.status} />
        </div>
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-slate-100">
          {!detail ? (
            <div className="py-6 text-center text-slate-400"><Loader2 size={20} className="animate-spin mx-auto" /></div>
          ) : (
            <>
              {/* Шаги */}
              <div className="mt-4 mb-5">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <BookOpen size={13} /> Шаги ({detail.steps.length})
                </p>
                <div className="space-y-1.5">
                  {detail.steps.map((s, i) => (
                    <div key={s.id} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2">
                      <span className="text-sm text-slate-700 truncate">
                        {i + 1}. {s.title} {s.require_quiz && <span className="text-slate-400">· тест</span>}
                      </span>
                      {isDraft && (
                        <button
                          onClick={() => deleteStep(s.id)}
                          disabled={busy}
                          className="text-slate-300 hover:text-red-500 flex-shrink-0 ml-2"
                          title="Убрать шаг"
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                    </div>
                  ))}
                  {detail.steps.length === 0 && (
                    <p className="text-sm text-slate-400">Нет шагов.</p>
                  )}
                </div>
              </div>

              {/* Действия */}
              <div className="flex flex-wrap items-center gap-2 mb-5">
                {isDraft && detail.steps.length > 0 && (
                  <button onClick={publish} disabled={busy} className="btn btn-primary">
                    <Send size={15} className="mr-2" /> Опубликовать
                  </button>
                )}
                {!isDraft && (
                  <div className="flex items-center gap-2">
                    <select
                      value={assignee}
                      onChange={(e) => setAssignee(e.target.value)}
                      className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 bg-white"
                    >
                      <option value="">Назначить сотруднику…</option>
                      {assignable.map((u) => (
                        <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
                      ))}
                    </select>
                    <button onClick={assign} disabled={busy || !assignee} className="btn btn-secondary disabled:opacity-40">
                      <Users size={15} className="mr-2" /> Назначить
                    </button>
                  </div>
                )}
                {msg && <span className="text-sm text-slate-500">{msg}</span>}
              </div>

              {/* Прогресс сотрудников */}
              {progress.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                    <BarChart3 size={13} /> Прогресс
                  </p>
                  <div className="space-y-1.5">
                    {progress.map((row) => (
                      <div key={row.enrollment_id} className="flex items-center justify-between text-sm">
                        <span className="text-slate-700">{userName(row.user_id)}</span>
                        <span className={`font-medium ${row.status === "completed" ? "text-green-600" : "text-slate-500"}`}>
                          {row.passed_steps}/{row.total_steps}
                          {row.status === "completed" && " ✓"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* ============================ Мелкие UI-кусочки ============================ */

function Header({ icon: Icon, title, subtitle, tight }) {
  return (
    <div className={tight ? "" : "mb-6"}>
      <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
        <Icon size={24} className="text-brand-600" /> {title}
      </h1>
      {subtitle && <p className="text-slate-500 mt-1">{subtitle}</p>}
    </div>
  );
}

function ProgressBar({ passed, total }) {
  const pct = total ? Math.round((passed / total) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-500 mb-1">
        <span>Пройдено {passed} из {total}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full bg-brand-500 transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    draft: ["Черновик", "bg-amber-50 text-amber-700 border-amber-200"],
    published: ["Опубликован", "bg-green-50 text-green-700 border-green-200"],
    archived: ["В архиве", "bg-slate-50 text-slate-500 border-slate-200"],
  };
  const [label, cls] = map[status] || [status, "bg-slate-50 text-slate-500 border-slate-200"];
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${cls} flex-shrink-0`}>{label}</span>;
}

function Loading() {
  return (
    <div className="max-w-3xl mx-auto space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-white rounded-xl border border-slate-200 h-24 animate-pulse" />
      ))}
    </div>
  );
}

function Empty({ icon: Icon, title, text }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 border-dashed p-12 text-center">
      <Icon size={40} className="text-slate-300 mx-auto mb-4" />
      <h3 className="text-lg font-bold text-slate-900 mb-1">{title}</h3>
      <p className="text-slate-500 max-w-md mx-auto">{text}</p>
    </div>
  );
}

function ErrorBox({ text }) {
  return (
    <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-100">{text}</div>
  );
}
