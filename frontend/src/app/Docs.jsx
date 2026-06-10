import { useEffect, useState, useCallback } from "react";
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
      <div className="app-head"><div className="eyebrow">Документы</div><h1 className="serif">Материалы двойника</h1></div>
      <div className="empty-note">Сначала создайте компанию слева, чтобы у двойника была папка для документов.</div>
    </div>
  );

  return (
    <div>
      <div className="app-head">
        <div className="eyebrow">Документы{companyName ? ` · ${companyName}` : ""}</div>
        <h1 className="serif">Материалы двойника</h1>
        <p>Профиль компании и всё, что двойник для неё подготовил.</p>
      </div>

      <div className="docs-layout">
        <div className="docs-list">
          <div className={"file-card" + (selected === "__profile__" ? " active" : "")} onClick={openProfile}>
            <div className="file-name">★ Профиль компании</div>
            <div className="file-meta">контекст для двойника</div>
          </div>
          {(data?.files || []).filter((f) => f.name !== "profile.md").map((f) => (
            <div key={f.name} className={"file-card" + (selected === f.name ? " active" : "")} onClick={() => openFile(f.name)}>
              <div className="file-name">{f.name}</div>
              <div className="file-meta">{Math.max(1, Math.round(f.size / 1024))} КБ</div>
            </div>
          ))}
          {(!data?.files || data.files.filter((f) => f.name !== "profile.md").length === 0) && (
            <div className="empty-note" style={{ padding: "24px 12px", fontSize: 13 }}>Документов пока нет.<br />Поручите двойнику задачу.</div>
          )}
        </div>

        <div className="docs-view">
          {selected === "__profile__" ? (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h2 className="serif" style={{ fontSize: 22 }}>Профиль компании</h2>
                {profileEdit
                  ? <span><button className="btn btn-ghost btn-sm" onClick={() => { setProfileEdit(false); setProfileDraft(data.profile || ""); }}>Отмена</button>
                          <button className="btn btn-primary btn-sm" style={{ marginLeft: 8 }} onClick={saveProfile}>Сохранить</button></span>
                  : <button className="btn btn-ghost btn-sm" onClick={() => setProfileEdit(true)}>Редактировать</button>}
              </div>
              {profileEdit
                ? <textarea value={profileDraft} onChange={(e) => setProfileDraft(e.target.value)} rows={18}
                    style={{ width: "100%", border: "1px solid var(--line)", borderRadius: 11, padding: 14, fontFamily: "inherit", fontSize: 14.5, outline: "none" }} />
                : <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(data?.profile || "_Профиль пуст._") }} />}
            </div>
          ) : selected ? (
            <div className="md" dangerouslySetInnerHTML={{ __html: renderMd(content) }} />
          ) : (
            <div className="placeholder">Выберите документ слева, чтобы открыть.</div>
          )}
        </div>
      </div>
    </div>
  );
}
