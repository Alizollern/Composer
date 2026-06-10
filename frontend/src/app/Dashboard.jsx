import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";
import Logo from "../components/Logo.jsx";
import CommandCenter from "./CommandCenter.jsx";
import Chat from "./Chat.jsx";
import Docs from "./Docs.jsx";
import History from "./History.jsx";
import NewCompanyModal from "./NewCompanyModal.jsx";

const NAV = [
  { id: "command", ico: "◆", label: "Командный центр" },
  { id: "chat", ico: "❝", label: "Диалог" },
  { id: "docs", ico: "▤", label: "Документы" },
  { id: "history", ico: "⟳", label: "История" },
];

export default function Dashboard() {
  const [view, setView] = useState("command");
  const [companies, setCompanies] = useState([]);
  const [company, setCompany] = useState("");
  const [online, setOnline] = useState(null);
  const [showNew, setShowNew] = useState(false);

  const loadCompanies = useCallback(async () => {
    try {
      const { companies } = await api.companies();
      setCompanies(companies);
      setCompany((cur) => cur || (companies[0] ? companies[0].slug : ""));
      return companies;
    } catch { return []; }
  }, []);

  useEffect(() => { loadCompanies(); }, [loadCompanies]);
  useEffect(() => {
    let alive = true;
    const ping = () => api.health().then(() => alive && setOnline(true)).catch(() => alive && setOnline(false));
    ping();
    const t = setInterval(ping, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  async function onCreated(c) {
    setShowNew(false);
    await loadCompanies();
    setCompany(c.slug);
  }

  const current = companies.find((c) => c.slug === company);

  return (
    <div className="app-shell">
      <aside className="app-side">
        <Link to="/" className="logo">
          <Logo /><span className="logo-name">Evergreen</span>
        </Link>

        <div className="company-switch">
          <div className="cl">Компания</div>
          {companies.length ? (
            <select value={company} onChange={(e) => setCompany(e.target.value)}>
              {companies.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
            </select>
          ) : (
            <div style={{ fontSize: 13, color: "#9cc1ae" }}>Пока нет компаний</div>
          )}
          <div className="add" onClick={() => setShowNew(true)}>＋ Новая компания</div>
        </div>

        <nav className="app-nav">
          {NAV.map((n) => (
            <button key={n.id} className={view === n.id ? "active" : ""} onClick={() => setView(n.id)}>
              <span style={{ width: 18, textAlign: "center", opacity: .85, fontSize: 13 }}>{n.ico}</span>
              {n.label}
            </button>
          ))}
        </nav>

        <div className="app-side-foot">
          <div className="status">
            <span className={"dot " + (online === null ? "" : online ? "on" : "off")} />
            {online === null ? "Подключение…" : online ? "Двойник на связи" : "Нет соединения"}
          </div>
          <Link to="/">← На сайт</Link>
        </div>
      </aside>

      <main className="app-main">
        {view === "command" && <CommandCenter company={company} companyName={current?.name} onProduced={loadCompanies} onOpenDocs={() => setView("docs")} />}
        {view === "chat" && <Chat />}
        {view === "docs" && <Docs company={company} companyName={current?.name} />}
        {view === "history" && <History onOpen={() => setView("command")} />}
      </main>

      {showNew && <NewCompanyModal onClose={() => setShowNew(false)} onCreated={onCreated} />}
    </div>
  );
}
