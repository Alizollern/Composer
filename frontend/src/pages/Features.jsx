import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ScrollText, Search, FileText, Building2, Activity, MessagesSquare, ArrowRight,
} from "lucide-react";
import Reveal, { container, item } from "../components/Reveal.jsx";

const FEATURES = [
  { ic: ScrollText, t: "Стандарты обслуживания", d: "Готовит регламенты сервиса по образцу мировых брендов и адаптирует под размер, бюджет и рынок вашей компании." },
  { ic: Search, t: "Анализ конкурентов", d: "Изучает игроков рынка, их позиционирование и цены, собирает сводку с источниками и выводами." },
  { ic: FileText, t: "Документы и регламенты", d: "Превращает задачу в чистый документ: планы запуска, инструкции, обращения к команде, отчёты." },
  { ic: Building2, t: "Контекст компании", d: "Каждая компания — своя папка с профилем и документами. Двойник работает в контексте выбранного бизнеса." },
  { ic: Activity, t: "Живой ход работы", d: "Видно каждый шаг двойника: что он ищет, что анализирует, на чём строит выводы — в реальном времени." },
  { ic: MessagesSquare, t: "Диалог", d: "Быстрые вопросы и советы по бизнесу — двойник держит контекст беседы." },
];

export default function Features() {
  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-1/2 top-0 h-72 w-[700px] -translate-x-1/2 rounded-full bg-emerald/10 blur-[110px]" />
      <div className="container-x relative pt-20 pb-24">
        <Reveal className="mx-auto max-w-2xl text-center">
          <span className="eyebrow">Возможности</span>
          <h1 className="mt-4 text-5xl sm:text-6xl font-semibold text-ink text-balance">Что умеет ваш двойник</h1>
          <p className="mt-5 text-lg text-ink-soft">
            Операционная работа, которую обычно делает команда заместителей — в одном помощнике.
          </p>
        </Reveal>

        <motion.div
          variants={container} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-80px" }}
          className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
        >
          {FEATURES.map((f) => (
            <motion.div key={f.t} variants={item} className="card card-hover">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald/10 text-emerald-600">
                <f.ic size={22} />
              </div>
              <h3 className="mt-5 text-xl font-semibold text-ink">{f.t}</h3>
              <p className="mt-2.5 text-[15px] leading-relaxed text-ink-soft">{f.d}</p>
            </motion.div>
          ))}
        </motion.div>

        <Reveal className="mt-16">
          <div className="relative overflow-hidden rounded-[2rem] bg-forest-900 px-8 py-14 text-center">
            <div className="pointer-events-none absolute inset-0 bg-grid-dark opacity-50" />
            <div className="pointer-events-none absolute left-1/2 top-0 h-60 w-96 -translate-x-1/2 rounded-full bg-emerald/25 blur-[90px]" />
            <h2 className="relative text-3xl sm:text-4xl font-semibold text-white">Посмотрите в деле</h2>
            <p className="relative mt-3 text-white/65">Поручите двойнику первую задачу — это займёт минуту.</p>
            <Link to="/app" className="btn btn-primary relative mt-7 px-6 py-3.5 text-base">
              Открыть двойника <ArrowRight size={18} />
            </Link>
          </div>
        </Reveal>
      </div>
    </div>
  );
}
