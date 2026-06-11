import { useEffect, useState, useCallback } from "react";
import { Star, FileText, Pencil, Save, X } from "lucide-react";
import { api } from "../lib/api.js";
import { renderMd } from "../lib/md.js";

export default function Docs({ company, companyName }) {
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null); // file name or "__profile__"
  const [content, setContent] = useState("");
  const [profileEdit, setProfileEdit] = useState(false);
  const [profileDraft, setProfileDraft] = useState("");

  const load = useCallback(async () => {
    if (!company) { setData(null); return; }
    try {
      const c = await api.company(company);
      setData(c);
      setProfileDraft(c.profile || "");
    } catch { setData(null); }
  }, [company]);

  useEffect(() => { load(); setSelected(null); setContent(""); setProfileEdit(false); }, [load]);

  async function openFile(name) {
    setSelected(name); setProfileEdit(false);
    try { const r = await api.companyFile(company, name); setContent(r.content); }
    catch { setContent("Не удалось открыть документ."); }
  }
  function openProfile() { setSelected("__profile__"); setProfileEdit(false); }
  async function saveProfile() {
    try { const c = await api.saveProfile(company, profileDraft); setData(c); setProfileEdit(false); }
    catch { /* ignore */ }
  }

  if (!company) return (
    <div>
      <div className="eyebrow">Документы</div>
      <h1 className="mt-2 text-3xl sm:text-4xl font-semibold text-ink">Материалы двойника</h1>
      <div className="mt-6 rounded-3xl border border-dashed border-line bg-white/60 p-10 text-center text-ink-muted">
        Сначала создайте компанию слева, чтобы у двойника была папка для документов.
      </div>
    </div>
  );

  const files = (data?.files || []).filter((f) => f.name !== "profile.md");

  return (
    <div>
      <div className="mb-6">
        <div className="eyebrow">Документы{companyName ? ` · ${companyName}` : ""}</div>
        <h1 className="mt-2 text-3xl sm:text-4xl font-semibold text-ink">Материалы двойника</h1>
        <p className="mt-2 text-ink-soft">Профиль компании и всё, что двойник для неё подготовил.</p>
      </div>

      <div className="grid gap-5 md:grid-cols-[260px_1fr]">
        {/* Список */}
        <div className="space-y-2">
          <button
            onClick={openProfile}
            className={
              "flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition-all " +
              (selected === "__profile__" ? "border-emerald/40 bg-emerald/5" : "border-line bg-white hover:border-emerald/30")
            }
          >
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-emerald/10 text-emerald-600"><Star size={16} /></span>
            <span>
              <span className="block text-[14.5px] font-medium text-ink">Профиль компании</span>
              <span className="block text-[12px] text-ink-muted">контекст для двойника</span>
            </span>
          </button>

          {files.map((f) => (
            <button
              key={f.name}
              onClick={() => openFile(f.name)}
              className={
                "flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition-all " +
                (selected === f.name ? "border-emerald/40 bg-emerald/5" : "border-line bg-white hover:border-emerald/30")
              }
            >
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-paper-deep text-ink-soft"><FileText size={16} /></span>
              <span className="min-w-0">
                <span className="block truncate text-[14.5px] font-medium text-ink">{f.name}</span>
                <span className="block text-[12px] text-ink-muted">{Math.max(1, Math.round(f.size / 1024))} КБ</span>
              </span>
            </button>
          ))}

          {files.length === 0 && (
            <div className="rounded-2xl border border-dashed border-line px-4 py-6 text-center text-[13px] text-ink-muted">
              Документов пока нет.<br />Поручите двойнику задачу.
            </div>
          )}
        </div>

        {/* Просмотр */}
        <div className="min-h-[300px] rounded-3xl border border-line bg-white p-7 shadow-soft">
          {selected === "__profile__" ? (
            <div>
              <div className="mb-5 flex items-center justify-between">
                <h2 className="font-serif text-2xl font-semibold text-ink">Профиль компании</h2>
                {profileEdit ? (
                  <div className="flex gap-2">
                    <button className="btn btn-ghost btn-sm" onClick={() => { setProfileEdit(false); setProfileDraft(data.profile || ""); }}>
                      <X size={15} /> Отмена
                    </button>
                    <button className="btn btn-primary btn-sm" onClick={saveProfile}><Save size={15} /> Сохранить</button>
                  </div>
                ) : (
                  <button className="btn btn-ghost btn-sm" onClick={() => setProfileEdit(true)}><Pencil size={15} /> Редактировать</button>
                )}
              </div>
              {profileEdit ? (
                <textarea
                  value={profileDraft}
                  onChange={(e) => setProfileDraft(e.target.value)}
                  rows={18}
                  className="w-full rounded-2xl border border-line bg-paper p-4 text-[15px] leading-relaxed text-ink outline-none focus:border-emerald focus:ring-4 focus:ring-emerald/10"
                />
              ) : (
                <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(data?.profile || "_Профиль пуст._") }} />
              )}
            </div>
          ) : selected ? (
            <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(content) }} />
          ) : (
            <div className="flex h-full min-h-[240px] items-center justify-center text-center text-sm text-ink-muted">
              Выберите документ слева, чтобы открыть.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
