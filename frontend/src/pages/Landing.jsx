import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight, ArrowUpRight, Check, Sparkles, FileText,
  Search, ScrollText, Building2, Activity, MessagesSquare,
} from "lucide-react";
import Reveal, { container, item } from "../components/Reveal.jsx";

/* ---------- Живое превью «Командного центра» ---------- */
const FLOW = [
  { t: "Принял задачу и распределил работу", s: "done" },
  { t: "Сбор информации по рынку и конкурентам", s: "done" },
  { t: "Анализ данных и формулировка выводов", s: "run" },
  { t: "Подготовка готового документа", s: "idle" },
];

function Preview() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 40, rotateX: 8 }}
      animate={{ opacity: 1, y: 0, rotateX: 0 }}
      transition={{ duration: 0.9, delay: 0.25, ease: [0.21, 0.6, 0.35, 1] }}
      style={{ transformPerspective: 1200 }}
      className="relative mx-auto mt-16 max-w-4xl"
    >
      <div className="absolute -inset-6 rounded-[2.4rem] bg-emerald/10 blur-3xl" />
      <div className="relative overflow-hidden rounded-3xl border border-line bg-white shadow-lift">
        {/* Шапка окна */}
        <div className="flex items-center gap-2 border-b border-line bg-paper/70 px-5 py-3.5">
          <span className="h-3 w-3 rounded-full bg-[#f5685b]" />
          <span className="h-3 w-3 rounded-full bg-[#f6bd4f]" />
          <span className="h-3 w-3 rounded-full bg-[#5fcd7e]" />
          <span className="ml-3 text-[13px] text-ink-muted">Evergreen · Командный центр</span>
        </div>

        <div className="grid sm:grid-cols-[200px_1fr]">
          {/* Боковая «постановка» */}
          <div className="hidden sm:block border-r border-line p-5 bg-paper/40">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted mb-3">Поручение</div>
            <div className="space-y-2">
              <div className="h-2.5 w-full rounded-full bg-ink/10" />
              <div className="h-2.5 w-4/5 rounded-full bg-ink/10" />
              <div className="h-2.5 w-3/5 rounded-full bg-ink/10" />
            </div>
            <div className="mt-6 text-xs font-semibold uppercase tracking-wider text-ink-muted mb-3">Компания</div>
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald/10 px-3 py-1.5 text-[13px] font-medium text-emerald-600">
              <Building2 size={13} /> Кофейня «Утро»
            </div>
          </div>

          {/* Лента работы */}
          <div className="p-6 space-y-3.5">
            {FLOW.map((f, i) => (
              <motion.div
                key={f.t}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 + i * 0.25, duration: 0.5 }}
                className="flex items-center gap-3"
              >
                <span
                  className={
                    "grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs " +
                    (f.s === "done"
                      ? "bg-emerald text-white"
                      : f.s === "run"
                      ? "bg-emerald/15 text-emerald-600 ring-2 ring-emerald/30"
                      : "bg-ink/5 text-ink-muted")
                  }
                >
                  {f.s === "done" ? <Check size={14} /> : f.s === "run" ? (
                    <span className="h-2 w-2 rounded-full bg-emerald animate-pulse-soft" />
                  ) : "•"}
                </span>
                <span className={"text-[14.5px] " + (f.s === "idle" ? "text-ink-muted" : "text-ink")}>{f.t}</span>
              </motion.div>
            ))}

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.9, duration: 0.6 }}
              className="mt-5 rounded-2xl border border-line bg-paper/60 p-4"
            >
              <div className="flex items-center gap-2 text-[13px] font-medium text-emerald-600">
                <FileText size={14} /> Анализ_конкурентов.md
              </div>
              <div className="mt-3 space-y-2">
                <div className="h-2 w-full rounded-full bg-ink/8" />
                <div className="h-2 w-11/12 rounded-full bg-ink/8" />
                <div className="h-2 w-2/3 rounded-full bg-ink/8" />
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* ---------- Контент ---------- */
const ABILITIES = [
  { ic: ScrollText, t: "Стандарты и процессы", d: "Готовит регламенты сервиса, инструкции и стандарты, адаптированные под вашу компанию и рынок." },
  { ic: Search, t: "Анализ и исследования", d: "Изучает конкурентов, рынок и тренды, собирает факты с источниками и делает выводы." },
  { ic: FileText, t: "Документы и решения", d: "Превращает данные в чёткие документы: планы, отчёты, обращения к команде." },
];

const STEPS = [
  { n: "01", t: "Опишите задачу", d: "Обычными словами, как поставили бы её заместителю. Без технических настроек." },
  { n: "02", t: "Двойник работает", d: "Собирает данные, анализирует, оформляет — вы видите каждый шаг в реальном времени." },
  { n: "03", t: "Получаете результат", d: "Готовый документ сохраняется в папке компании. Копится база знаний бизнеса." },
];

const SHOWCASE = [
  { ic: Building2, t: "Контекст компании", d: "Свой профиль и папка документов на каждый бизнес." },
  { ic: Activity, t: "Видно ход работы", d: "Каждый шаг двойника — в реальном времени." },
  { ic: MessagesSquare, t: "Диалог", d: "Быстрые вопросы и советы, с памятью беседы." },
];

export default function Landing() {
  return (
    <>
      {/* ===== HERO ===== */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-grid opacity-60 [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />
        <div className="pointer-events-none absolute left-1/2 top-[-10%] h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-emerald/15 blur-[120px]" />

        <div className="container-x relative pt-20 pb-10 sm:pt-28 text-center">
          <motion.span
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="eyebrow rounded-full border border-emerald/25 bg-emerald/5 px-3.5 py-1.5"
          >
            <Sparkles size={13} /> Цифровой двойник руководителя
          </motion.span>

          <motion.h1
            initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.05 }}
            className="mx-auto mt-7 max-w-4xl text-balance text-5xl sm:text-6xl lg:text-7xl font-semibold leading-[1.02] text-ink"
          >
            Двойник ведёт операционку,<br className="hidden sm:block" />{" "}
            пока вы <em className="italic text-emerald-600">ведёте бизнес</em>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.15 }}
            className="mx-auto mt-7 max-w-2xl text-lg sm:text-xl leading-relaxed text-ink-soft text-balance"
          >
            Опишите задачу обычными словами — Evergreen соберёт данные, проанализирует
            и подготовит стандарты, отчёты и решения. Как опытный заместитель,
            который работает 24/7 и знает контекст вашей компании.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.25 }}
            className="mt-9 flex flex-wrap items-center justify-center gap-3"
          >
            <Link to="/app" className="btn btn-primary px-6 py-3.5 text-base">
              Открыть двойника <ArrowRight size={18} />
            </Link>
            <Link to="/features" className="btn btn-ghost px-6 py-3.5 text-base">Что он умеет</Link>
          </motion.div>

          {/* Доверие */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.7, delay: 0.4 }}
            className="mx-auto mt-12 flex max-w-xl flex-wrap items-stretch justify-center divide-x divide-line rounded-2xl"
          >
            {[
              ["24/7", "всегда на связи"],
              ["минуты", "вместо недель на задачу"],
              ["∞", "компаний и проектов"],
            ].map(([n, l]) => (
              <div key={l} className="px-6 py-1 text-center">
                <div className="font-serif text-2xl font-semibold text-ink">{n}</div>
                <div className="mt-1 text-[13px] text-ink-muted">{l}</div>
              </div>
            ))}
          </motion.div>

          <Preview />
        </div>
      </section>

      {/* ===== ВОЗМОЖНОСТИ ===== */}
      <section className="container-x py-24 sm:py-28">
        <Reveal className="mx-auto max-w-2xl text-center">
          <span className="eyebrow">Что он умеет</span>
          <h2 className="mt-4 text-4xl sm:text-5xl font-semibold text-ink text-balance">
            Один двойник — вся операционная работа
          </h2>
          <p className="mt-4 text-lg text-ink-soft">
            Не набор разрозненных инструментов, а единый помощник, который держит контекст вашего бизнеса.
          </p>
        </Reveal>

        <motion.div
          variants={container} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-80px" }}
          className="mt-14 grid gap-6 md:grid-cols-3"
        >
          {ABILITIES.map((f) => (
            <motion.div key={f.t} variants={item} className="card card-hover">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald/10 text-emerald-600">
                <f.ic size={22} />
              </div>
              <h3 className="mt-5 text-xl font-semibold text-ink">{f.t}</h3>
              <p className="mt-2.5 text-[15px] leading-relaxed text-ink-soft">{f.d}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ===== КАК РАБОТАЕТ ===== */}
      <section className="bg-paper-deep/60 border-y border-line">
        <div className="container-x py-24 sm:py-28">
          <Reveal className="mx-auto max-w-2xl text-center">
            <span className="eyebrow">Как это работает</span>
            <h2 className="mt-4 text-4xl sm:text-5xl font-semibold text-ink text-balance">
              Три шага — от задачи до результата
            </h2>
          </Reveal>

          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <Reveal key={s.n} delay={i * 0.1}>
                <div className="relative h-full rounded-3xl bg-white border border-line p-7 shadow-soft">
                  <div className="font-serif text-5xl font-semibold text-emerald/25">{s.n}</div>
                  <h3 className="mt-3 text-xl font-semibold text-ink">{s.t}</h3>
                  <p className="mt-2.5 text-[15px] leading-relaxed text-ink-soft">{s.d}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ===== ТЁМНАЯ ВИТРИНА ===== */}
      <section className="container-x py-24 sm:py-28">
        <div className="relative overflow-hidden rounded-[2.5rem] bg-forest-900 px-7 py-16 sm:px-14 sm:py-20">
          <div className="pointer-events-none absolute inset-0 bg-grid-dark opacity-50" />
          <div className="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full bg-emerald/25 blur-[100px]" />
          <div className="relative grid gap-12 lg:grid-cols-2 lg:items-center">
            <div>
              <span className="eyebrow text-emerald-400">Почему это работает</span>
              <h2 className="mt-4 text-4xl sm:text-5xl font-semibold text-white text-balance leading-[1.05]">
                Не чат без следа,<br /> а заместитель с памятью
              </h2>
              <p className="mt-5 text-lg leading-relaxed text-white/65">
                Каждая компания — своя папка с профилем и документами. Двойник
                работает в её контексте и накапливает базу знаний вашего бизнеса.
              </p>
              <Link to="/app" className="btn btn-primary mt-8 px-6 py-3.5 text-base">
                Попробовать <ArrowUpRight size={18} />
              </Link>
            </div>
            <div className="grid gap-4 sm:grid-cols-1">
              {SHOWCASE.map((f) => (
                <Reveal key={f.t} as="div">
                  <div className="flex items-start gap-4 rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur transition-colors hover:bg-white/10">
                    <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-emerald/20 text-emerald-400">
                      <f.ic size={20} />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">{f.t}</h3>
                      <p className="mt-1 text-[15px] text-white/60">{f.d}</p>
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ===== CTA ===== */}
      <section className="container-x pb-28">
        <Reveal className="mx-auto max-w-3xl text-center">
          <h2 className="text-4xl sm:text-5xl font-semibold text-ink text-balance">
            Передайте рутину двойнику
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-ink-soft">
            Освободите время для решений, которые двигают бизнес. Остальное двойник возьмёт на себя.
          </p>
          <Link to="/app" className="btn btn-primary mt-8 px-7 py-4 text-base">
            Начать сейчас <ArrowRight size={18} />
          </Link>
        </Reveal>
      </section>
    </>
  );
}
