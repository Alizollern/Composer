import { useEffect, useState } from "react";
import { Outlet, NavLink, Link, useLocation } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import Logo from "./Logo.jsx";

const NAV = [
  { to: "/features", label: "Возможности" },
  { to: "/pricing", label: "Цены" },
  { to: "/about", label: "О нас" },
  { to: "/contact", label: "Контакты" },
];

export default function SiteLayout() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const loc = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  useEffect(() => { setOpen(false); window.scrollTo(0, 0); }, [loc.pathname]);

  return (
    <div className="min-h-screen flex flex-col">
      <header
        className={
          "sticky top-0 z-50 transition-all duration-300 " +
          (scrolled
            ? "bg-paper/80 backdrop-blur-xl border-b border-line shadow-[0_1px_0_rgba(19,33,27,.04)]"
            : "bg-transparent border-b border-transparent")
        }
      >
        <div className="container-x flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 font-serif text-[19px] font-semibold text-ink">
            <Logo />
            <span>Evergreen</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  "px-3.5 py-2 rounded-full text-[15px] transition-colors " +
                  (isActive ? "text-emerald-600 font-medium" : "text-ink-soft hover:text-ink")
                }
              >
                {n.label}
              </NavLink>
            ))}
            <Link to="/app" className="btn btn-primary btn-sm ml-2">
              Открыть двойника <ArrowUpRight size={16} />
            </Link>
          </nav>

          {/* Мобильное меню */}
          <button
            className="md:hidden grid place-items-center w-10 h-10 rounded-xl border border-line text-ink"
            onClick={() => setOpen((v) => !v)}
            aria-label="Меню"
          >
            <span className="relative block w-5 h-3">
              <span className={"absolute left-0 top-0 h-0.5 w-5 bg-current transition-all " + (open ? "translate-y-1.5 rotate-45" : "")} />
              <span className={"absolute left-0 bottom-0 h-0.5 w-5 bg-current transition-all " + (open ? "-translate-y-1 -rotate-45" : "")} />
            </span>
          </button>
        </div>

        {open && (
          <div className="md:hidden border-t border-line bg-paper/95 backdrop-blur-xl">
            <div className="container-x py-4 flex flex-col gap-1">
              {NAV.map((n) => (
                <NavLink key={n.to} to={n.to} className="px-3 py-3 rounded-xl text-ink-soft hover:bg-white">
                  {n.label}
                </NavLink>
              ))}
              <Link to="/app" className="btn btn-primary mt-2">Открыть двойника</Link>
            </div>
          </div>
        )}
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="bg-forest-900 text-white/70 mt-24">
        <div className="container-x py-16">
          <div className="grid gap-10 md:grid-cols-[1.6fr_1fr_1fr]">
            <div className="max-w-sm">
              <Link to="/" className="flex items-center gap-2.5 font-serif text-xl font-semibold text-white">
                <Logo />
                <span>Evergreen</span>
              </Link>
              <p className="mt-4 text-[15px] leading-relaxed text-white/60">
                Цифровой двойник руководителя. Поручайте операционную работу —
                двойник соберёт данные, проанализирует и подготовит готовый результат.
              </p>
            </div>
            <div>
              <h4 className="text-white font-semibold text-sm uppercase tracking-wider mb-4">Продукт</h4>
              <div className="flex flex-col gap-2.5 text-[15px]">
                <Link to="/features" className="hover:text-white transition-colors">Возможности</Link>
                <Link to="/pricing" className="hover:text-white transition-colors">Цены</Link>
                <Link to="/app" className="hover:text-white transition-colors">Открыть двойника</Link>
              </div>
            </div>
            <div>
              <h4 className="text-white font-semibold text-sm uppercase tracking-wider mb-4">Компания</h4>
              <div className="flex flex-col gap-2.5 text-[15px]">
                <Link to="/about" className="hover:text-white transition-colors">О нас</Link>
                <Link to="/contact" className="hover:text-white transition-colors">Контакты</Link>
              </div>
            </div>
          </div>
          <div className="mt-14 pt-7 border-t border-white/10 flex flex-col sm:flex-row gap-2 justify-between text-sm text-white/45">
            <span>© {new Date().getFullYear()} Evergreen. Все права защищены.</span>
            <span>Сделано для руководителей.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
