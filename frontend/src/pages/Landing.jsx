import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <main>
      {/* Hero */}
      <section className="hero">
        <div className="hero-glow" />
        <div className="container">
          <span className="eyebrow">● Цифровой двойник руководителя</span>
          <h1 className="serif">
            Ваш двойник <em>ведёт операционку</em>, пока вы ведёте бизнес
          </h1>
          <p className="sub">
            Опишите задачу обычными словами — Evergreen соберёт данные, проанализирует,
            подготовит стандарты, отчёты и решения. Как опытный заместитель, который
            работает 24/7 и знает контекст вашей компании.
          </p>
          <div className="hero-actions">
            <Link to="/app" className="btn btn-primary">Открыть двойника →</Link>
            <Link to="/features" className="btn btn-ghost">Что он умеет</Link>
          </div>
          <div className="hero-trust">
            <div className="stat"><div className="num serif">24/7</div><div className="lbl">всегда на связи</div></div>
            <div className="stat"><div className="num serif">мин.</div><div className="lbl">а не недели на задачу</div></div>
            <div className="stat"><div className="num serif">∞</div><div className="lbl">компаний и проектов</div></div>
          </div>

          {/* Product preview */}
          <div className="preview">
            <div className="preview-bar">
              <span className="dot3" /><span className="dot3" /><span className="dot3" />
              <span className="ttl">Evergreen · Командный центр</span>
            </div>
            <div className="preview-body">
              <div className="preview-side">
                <div style={{ fontSize: 13, color: "#6f8076", marginBottom: 12 }}>Поручение</div>
                <div className="pl m" /><div className="pl s" /><div className="pl" />
                <div style={{ height: 18 }} />
                <div style={{ fontSize: 13, color: "#6f8076", marginBottom: 12 }}>Компания</div>
                <div className="pl s" />
              </div>
              <div className="preview-main">
                <div className="flow-step"><span className="flow-ic done">✓</span><span className="flow-tx">Принял задачу и распределил работу</span></div>
                <div className="flow-step"><span className="flow-ic done">✓</span><span className="flow-tx">Сбор информации по рынку</span></div>
                <div className="flow-step"><span className="flow-ic">▶</span><span className="flow-tx">Анализ конкурентов и выводы</span></div>
                <div className="flow-step"><span className="flow-ic idle">•</span><span className="flow-tx">Подготовка готового документа</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* What it does */}
      <section className="section">
        <div className="container">
          <div className="section-head">
            <h2 className="serif">Один двойник — вся операционная работа</h2>
            <p>Не набор разрозненных инструментов, а единый помощник, который держит контекст вашего бизнеса.</p>
          </div>
          <div className="cards">
            <div className="card"><div className="ic">◆</div><h3>Стандарты и процессы</h3><p>Готовит стандарты сервиса, регламенты и инструкции, адаптированные под вашу компанию и рынок.</p></div>
            <div className="card"><div className="ic">◷</div><h3>Анализ и исследования</h3><p>Изучает конкурентов, рынок и тренды, собирает факты с источниками и делает выводы.</p></div>
            <div className="card"><div className="ic">✎</div><h3>Документы и решения</h3><p>Превращает данные в чёткие документы: планы, отчёты, обращения к команде.</p></div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="section alt">
        <div className="container">
          <div className="section-head">
            <h2 className="serif">Как это работает</h2>
            <p>Три шага — от задачи до готового результата в папке вашей компании.</p>
          </div>
          <div className="steps">
            <div className="step"><div className="n serif">1</div><h3>Опишите задачу</h3><p>Обычными словами, как поставили бы её заместителю. Без технических настроек.</p></div>
            <div className="step"><div className="n serif">2</div><h3>Двойник работает</h3><p>Собирает данные, анализирует, оформляет — вы видите каждый шаг в реальном времени.</p></div>
            <div className="step"><div className="n serif">3</div><h3>Получаете результат</h3><p>Готовый документ сохраняется в папке компании. Накапливается база знаний бизнеса.</p></div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="section">
        <div className="container">
          <div className="cta-band">
            <div className="hero-glow" />
            <h2 className="serif">Передайте рутину двойнику</h2>
            <p>Освободите время для решений, которые двигают бизнес. Двойник возьмёт остальное.</p>
            <Link to="/app" className="btn btn-primary">Начать сейчас →</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
