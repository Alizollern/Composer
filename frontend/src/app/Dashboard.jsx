import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  LayoutGrid, MessagesSquare, FolderOpen, History as HistoryIcon,
  Plus, ChevronLeft, ChevronDown,
} from "lucide-react";
import { api } from "../lib/api.js";
import Logo from "../components/Logo.jsx";
import CommandCenter from "./CommandCenter.jsx";
import Chat from "./Chat.jsx";
import Docs from "./Docs.jsx";
import History from "./History.jsx";
import NewCompanyModal from "./NewCompanyModal.jsx";

const NAV = [
  { id: "command", ico: LayoutGrid, label: "Командный центр" },
  { id: "chat", ico: MessagesSquare, label: "Диалог" },
  { id: "docs", ico: FolderOpen, label: "Документы" },
  { id: "history", ico: HistoryIcon, label: "История" },
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
    <div className="min-h-screen bg-paper md:grid md:grid-cols-[270px_1fr]">
      {/* ===== Сайдбар ===== */}
      <aside className="flex flex-col bg-forest-900 text-white/80 md:sticky md:top-0 md:h-screen">
        <div className="flex items-center gap-2.5 px-6 py-6">
          <Logo />
          <Link to="/" className="font-serif text-xl font-semibold text-white">Evergreen</Link>
        </div>

        {/* Переключатель компании */}
        <div className="px-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
            <div className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-wider text-white/40">Компания</div>
            {companies.length ? (
              <div className="relative">
                <select
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="w-full appearance-none rounded-xl border border-white/10 bg-forest-800 px-3 py-2.5 pr-9 text-[15px] font-medium text-white outline-none focus:border-emerald/50"
                >
                  {companies.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
                </select>
                <ChevronDown size={16} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-white/40" />
              </div>
            ) : (
              <div className="px-1 py-1 text-[13px] text-white/45">Пока нет компаний</div>
            )}
            <button
              onClick={() => setShowNew(true)}
              className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-white/20 px-3 py-2 text-[13px] font-medium text-emerald-400 transition-colors hover:border-emerald/50 hover:bg-white/5"
            >
              <Plus size={14} /> Новая компания
            </button>
          </div>
        </div>

        {/* Навигация */}
        <nav className="mt-5 flex flex-col gap-1 px-4">
          {NAV.map((n) => {
            const active = view === n.id;
            return (
              <button
                key={n.id}
                onClick={() => setView(n.id)}
                className={
                  "flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-[15px] transition-all " +
                  (active ? "bg-emerald text-white shadow-[0_6px_18px_-8px_rgba(21,160,107,.9)]" : "text-white/65 hover:bg-white/5 hover:text-white")
                }
              >
                <n.ico size={18} className={active ? "opacity-100" : "opacity-70"} />
                {n.label}
              </button>
            );
          })}
        </nav>

        <div className="mt-auto p-4">
          <div className="flex items-center gap-2 px-2 py-2 text-[13px] text-white/55">
            <span
              className={
                "h-2 w-2 rounded-full " +
                (online === null ? "bg-white/30" : online ? "bg-emerald-400 animate-pulse-soft" : "bg-red-400")
              }
            />
            {online === null ? "Подключение…" : online ? "Двойник на связи" : "Нет соединения"}
          </div>
          <Link to="/" className="mt-1 flex items-center gap-1.5 rounded-xl px-2 py-2 text-[13px] text-white/50 transition-colors hover:text-white">
            <ChevronLeft size={14} /> На сайт
          </Link>
        </div>
      </aside>

      {/* ===== Контент ===== */}
      <main className="px-5 py-8 sm:px-10 sm:py-12">
        <div className="mx-auto max-w-5xl">
          {view === "command" && <CommandCenter company={company} companyName={current?.name} onProduced={loadCompanies} onOpenDocs={() => setView("docs")} />}
          {view === "chat" && <Chat />}
          {view === "docs" && <Docs company={company} companyName={current?.name} />}
          {view === "history" && <History onOpen={() => setView("command")} />}
        </div>
      </main>

      {showNew && <NewCompanyModal onClose={() => setShowNew(false)} onCreated={onCreated} />}
    </div>
  );
}
