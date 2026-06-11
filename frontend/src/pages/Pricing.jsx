import { Link } from "react-router-dom";
import { Check } from "lucide-react";
import Reveal from "../components/Reveal.jsx";

const PLANS = [
  {
    name: "Старт", price: "0", per: "пробный период", featured: false,
    desc: "Познакомиться с двойником и проверить на своих задачах.",
    feats: ["1 компания", "Командный центр и диалог", "Документы в папке компании", "Базовый контекст бизнеса"],
    cta: "Начать бесплатно", to: "/app",
  },
  {
    name: "Бизнес", price: "29 900 ₸", per: "в месяц", featured: true,
    desc: "Для активной операционной работы одной компании.",
    feats: ["До 3 компаний", "Безлимит поручений", "Анализ конкурентов и рынка", "История и накопление документов", "Приоритетная обработка"],
    cta: "Выбрать Бизнес", to: "/app",
  },
  {
    name: "Сеть", price: "Договорная", per: "", featured: false,
    desc: "Для сетей и групп компаний с несколькими брендами.",
    feats: ["Неограниченно компаний", "Командная работа", "Интеграции с вашими системами", "Выделенная поддержка"],
    cta: "Связаться", to: "/contact",
  },
];

export default function Pricing() {
  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-1/2 top-0 h-72 w-[700px] -translate-x-1/2 rounded-full bg-emerald/10 blur-[110px]" />
      <div className="container-x relative pt-20 pb-24">
        <Reveal className="mx-auto max-w-2xl text-center">
          <span className="eyebrow">Цены</span>
          <h1 className="mt-4 text-5xl sm:text-6xl font-semibold text-ink text-balance">Простые тарифы</h1>
          <p className="mt-5 text-lg text-ink-soft">
            Платите за результат, а не за количество кнопок. Начните бесплатно.
          </p>
        </Reveal>

        <div className="mt-16 grid items-stretch gap-6 lg:grid-cols-3">
          {PLANS.map((p, i) => (
            <Reveal key={p.name} delay={i * 0.1}>
              <div
                className={
                  "relative flex h-full flex-col rounded-3xl border p-8 transition-all " +
                  (p.featured
                    ? "border-emerald/40 bg-forest-900 text-white shadow-lift lg:-mt-4 lg:mb-0"
                    : "border-line bg-white shadow-soft hover:-translate-y-1 hover:shadow-lift")
                }
              >
                {p.featured && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-emerald px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-white">
                    Популярный
                  </span>
                )}
                <h3 className="font-serif text-2xl font-semibold">{p.name}</h3>
                <div className="mt-3 font-serif text-4xl font-semibold">
                  {p.price}
                  {p.per && <span className={"ml-1.5 text-base font-sans font-normal " + (p.featured ? "text-white/55" : "text-ink-muted")}>/ {p.per}</span>}
                </div>
                <p className={"mt-3 text-[15px] " + (p.featured ? "text-white/65" : "text-ink-soft")}>{p.desc}</p>

                <ul className="mt-7 space-y-3">
                  {p.feats.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-[15px]">
                      <Check size={18} className={"mt-0.5 shrink-0 " + (p.featured ? "text-emerald-400" : "text-emerald-600")} />
                      <span className={p.featured ? "text-white/85" : "text-ink-soft"}>{f}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  to={p.to}
                  className={"btn mt-8 w-full " + (p.featured ? "btn-primary" : "btn-ghost")}
                >
                  {p.cta}
                </Link>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </div>
  );
}
