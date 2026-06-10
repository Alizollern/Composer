import { Link } from "react-router-dom";

const PLANS = [
  { name: "Старт", price: "0", per: "пробный период", desc: "Познакомиться с двойником и проверить на своих задачах.", featured: false,
    feats: ["1 компания", "Командный центр и диалог", "Документы в папке компании", "Базовый контекст бизнеса"], cta: "Начать бесплатно" },
  { name: "Бизнес", price: "29 900 ₸", per: "в месяц", desc: "Для активной операционной работы одной компании.", featured: true,
    feats: ["До 3 компаний", "Безлимит поручений", "Анализ конкурентов и рынок", "История и накопление документов", "Приоритетная обработка"], cta: "Выбрать Бизнес" },
  { name: "Сеть", price: "Договорная", per: "", desc: "Для сетей и групп компаний с несколькими брендами.", featured: false,
    feats: ["Неограниченно компаний", "Командная работа", "Интеграции с вашими системами", "Выделенная поддержка"], cta: "Связаться" },
];

export default function Pricing() {
  return (
    <main className="page">
      <div className="container">
        <span className="eyebrow">Цены</span>
        <h1 className="serif" style={{ marginTop: 16 }}>Простые тарифы</h1>
        <p className="lead">Платите за результат, а не за количество кнопок. Начните бесплатно.</p>

        <div className="pricing" style={{ marginTop: 44 }}>
          {PLANS.map((p) => (
            <div className={"plan" + (p.featured ? " featured" : "")} key={p.name}>
              {p.featured && <span className="tag">Популярный</span>}
              <h3 className="serif">{p.name}</h3>
              <div className="price serif">{p.price} {p.per && <span>/ {p.per}</span>}</div>
              <p className="desc">{p.desc}</p>
              <ul>{p.feats.map((f) => <li key={f}>{f}</li>)}</ul>
              <Link to={p.name === "Сеть" ? "/contact" : "/app"}
                    className={"btn " + (p.featured ? "btn-primary" : "btn-ghost")}
                    style={{ justifyContent: "center" }}>{p.cta}</Link>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
