import { useState } from "react";
import { X, Loader2 } from "lucide-react";
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
    } catch { setErr("Не удалось создать. Попробуйте ещё раз."); setBusy(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-forest-900/40 p-4 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-lg rounded-3xl bg-white p-7 shadow-lift" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <h3 className="font-serif text-2xl font-semibold text-ink">Новая компания</h3>
          <button className="grid h-9 w-9 place-items-center rounded-full text-ink-muted hover:bg-paper-deep" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="field mt-5">
          <label>Название</label>
          <input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Например: Кофейня «Утро»" />
        </div>
        <div className="field">
          <label>Профиль компании <span className="font-normal text-ink-muted">(можно заполнить позже)</span></label>
          <textarea rows={8} value={profile} onChange={(e) => setProfile(e.target.value)} placeholder={PLACEHOLDER} className="font-sans" />
        </div>

        {err && <div className="mb-3 text-sm text-red-500">{err}</div>}

        <div className="flex justify-end gap-2">
          <button className="btn btn-ghost" onClick={onClose}>Отмена</button>
          <button className="btn btn-primary" disabled={busy || !name.trim()} onClick={create}>
            {busy ? <><Loader2 size={16} className="animate-spin" /> Создаём…</> : "Создать компанию"}
          </button>
        </div>
      </div>
    </div>
  );
}
