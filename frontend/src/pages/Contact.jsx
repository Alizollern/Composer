import { useState } from "react";

export default function Contact() {
  const [sent, setSent] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", message: "" });

  function submit(e) {
    e.preventDefault();
    // открываем почтовый клиент с заполненным письмом
    const body = encodeURIComponent(`${form.message}\n\n— ${form.name} (${form.email})`);
    window.location.href = `mailto:hello@evergreen.ai?subject=${encodeURIComponent("Заявка с сайта Evergreen")}&body=${body}`;
    setSent(true);
  }

  return (
    <main className="page">
      <div className="container">
        <span className="eyebrow">Контакты</span>
        <h1 className="serif" style={{ marginTop: 16 }}>Поговорим о вашем бизнесе</h1>
        <p className="lead">Расскажите о компании и задачах — подберём, как двойник может помочь.</p>

        <div className="contact-grid" style={{ marginTop: 44 }}>
          <form onSubmit={submit}>
            <div className="field">
              <label>Имя</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Как к вам обращаться" />
            </div>
            <div className="field">
              <label>Email</label>
              <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@company.com" />
            </div>
            <div className="field">
              <label>Сообщение</label>
              <textarea rows={5} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Коротко о компании и задачах" />
            </div>
            <button className="btn btn-primary" type="submit">{sent ? "Спасибо!" : "Отправить"}</button>
          </form>

          <div className="card">
            <h3 className="serif" style={{ fontSize: 20, marginBottom: 12 }}>Прямой контакт</h3>
            <p style={{ color: "var(--muted-solid)", marginBottom: 18 }}>
              Предпочитаете написать напрямую — мы всегда на связи.
            </p>
            <p style={{ marginBottom: 8 }}><strong>Почта:</strong> hello@evergreen.ai</p>
            <p style={{ marginBottom: 8 }}><strong>Telegram:</strong> @evergreen</p>
            <p style={{ color: "var(--muted-solid)", marginTop: 18, fontSize: 14 }}>
              Отвечаем в течение рабочего дня.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
