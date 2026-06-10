import { useState } from "react";
import { api } from "../lib/api.js";

const PLACEHOLDER = `# Название компании

- Сфера: например, сеть кофеен
- Размер: 3 точки, Алматы
- Средний чек, аудитория, бюджет
- Чем отличаемся / tone of voice`;

export default function NewCompanyModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [profile, setProfile] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function create() {
    if (!name.trim() || busy) return;
    setBusy(true); setErr("");
    try {
      const c = await api.createCompany(name.trim(), profile.trim());
      onCreated(c);
    } catch (e) { setErr("Не удалось создать. Попробуйте ещё раз."); setBusy(false); }
  }

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3 className="serif">Новая компания</h3>
        <div className="field">
          <label>Название</label>
          <input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Например: Кофейня «Утро»" />
        </div>
        <div className="field">
          <label>Профиль компании <span style={{ color: "var(--muted-solid)", fontWeight: 400 }}>(можно заполнить позже)</span></label>
          <textarea rows={8} value={profile} onChange={(e) => setProfile(e.target.value)} placeholder={PLACEHOLDER}
            style={{ fontFamily: "inherit", fontSize: 14 }} />
        </div>
        {err && <div style={{ color: "var(--danger)", fontSize: 13, marginBottom: 8 }}>{err}</div>}
        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onClose}>Отмена</button>
          <button className="btn btn-primary" disabled={busy || !name.trim()} onClick={create}>
            {busy ? "Создаём…" : "Создать компанию"}
          </button>
        </div>
      </div>
    </div>
  );
}
