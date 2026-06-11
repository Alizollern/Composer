import { Target, Eye, FileCheck } from "lucide-react";
import Reveal from "../components/Reveal.jsx";

const VALUES = [
  { ic: Target, t: "Контекст важнее команд", d: "Двойник держит профиль вашей компании и адаптирует каждое решение под неё, а не выдаёт шаблон." },
  { ic: Eye, t: "Прозрачность", d: "Вы видите, как двойник работает: какие шаги делает и на чём основывает выводы." },
  { ic: FileCheck, t: "Результат, а не разговоры", d: "На выходе — готовый документ в папке компании, а не очередной чат без следа." },
];

export default function About() {
  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-1/2 top-0 h-72 w-[700px] -translate-x-1/2 rounded-full bg-emerald/10 blur-[110px]" />
      <div className="container-x relative pt-20 pb-24">
        <Reveal className="mx-auto max-w-3xl text-center">
          <span className="eyebrow">О нас</span>
          <h1 className="mt-4 text-4xl sm:text-5xl font-semibold text-ink text-balance leading-[1.08]">
            Мы создаём двойника, которому можно доверить дело
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-ink-soft text-balance">
            Evergreen рождается из простой идеи: у каждого руководителя должен быть
            надёжный заместитель, который понимает контекст бизнеса и берёт на себя
            операционную работу — быстро, тщательно и без выходных.
          </p>
        </Reveal>

        <div className="mx-auto mt-16 grid max-w-4xl gap-12 sm:grid-cols-2">
          <Reveal>
            <h2 className="font-serif text-2xl font-semibold text-ink">Зачем мы это делаем</h2>
            <p className="mt-3 text-[15.5px] leading-relaxed text-ink-soft">
              Руководитель малого и среднего бизнеса тонет в операционке: стандарты,
              анализ конкурентов, документы, ответы команде. На стратегию не остаётся
              времени. Мы переносим эту рутину на цифрового двойника, который работает
              в контексте именно вашей компании.
            </p>
          </Reveal>
          <Reveal delay={0.1}>
            <h2 className="font-serif text-2xl font-semibold text-ink">Куда мы идём</h2>
            <p className="mt-3 text-[15.5px] leading-relaxed text-ink-soft">
              Сегодня двойник ведёт операционную работу. Завтра — подключается к вашим
              системам, держит память по каждому проекту и становится полноценным
              цифровым заместителем команды руководителя.
            </p>
          </Reveal>
        </div>

        <Reveal className="mx-auto mt-20 max-w-2xl text-center">
          <span className="eyebrow">Во что мы верим</span>
        </Reveal>
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {VALUES.map((v, i) => (
            <Reveal key={v.t} delay={i * 0.1}>
              <div className="card h-full">
                <div className="grid h-11 w-11 place-items-center rounded-2xl bg-emerald/10 text-emerald-600">
                  <v.ic size={20} />
                </div>
                <h3 className="mt-4 font-serif text-xl font-semibold text-ink">{v.t}</h3>
                <p className="mt-2.5 text-[15px] leading-relaxed text-ink-soft">{v.d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </div>
  );
}
