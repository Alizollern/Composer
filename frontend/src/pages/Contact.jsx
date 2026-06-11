import { useState } from "react";
import { Mail, Send, MessageCircle } from "lucide-react";
import Reveal from "../components/Reveal.jsx";

export default function Contact() {
  const [sent, setSent] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", message: "" });

  function submit(e) {
    e.preventDefault();
    const body = encodeURIComponent(`${form.message}\n\n— ${form.name} (${form.email})`);
    window.location.href = `mailto:hello@evergreen.ai?subject=${encodeURIComponent("Заявка с сайта Evergreen")}&body=${body}`;
    setSent(true);
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-1/2 top-0 h-72 w-[700px] -translate-x-1/2 rounded-full bg-emerald/10 blur-[110px]" />
      <div className="container-x relative pt-20 pb-24">
        <Reveal className="mx-auto max-w-2xl text-center">
          <span className="eyebrow">Контакты</span>
          <h1 className="mt-4 text-5xl sm:text-6xl font-semibold text-ink text-balance">Поговорим о вашем бизнесе</h1>
          <p className="mt-5 text-lg text-ink-soft">
            Расскажите о компании и задачах — подберём, как двойник может помочь.
          </p>
        </Reveal>

        <div className="mx-auto mt-16 grid max-w-4xl gap-6 lg:grid-cols-[1.3fr_1fr]">
          <Reveal>
            <form onSubmit={submit} className="card">
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
              <button className="btn btn-primary w-full" type="submit">
                {sent ? "Спасибо!" : <>Отправить <Send size={16} /></>}
              </button>
            </form>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="card h-full bg-forest-900 text-white border-forest-700">
              <h3 className="font-serif text-xl font-semibold">Прямой контакт</h3>
              <p className="mt-3 text-[15px] text-white/65">
                Предпочитаете написать напрямую — мы всегда на связи.
              </p>
              <div className="mt-6 space-y-4">
                <a href="mailto:hello@evergreen.ai" className="flex items-center gap-3 text-[15px] hover:text-emerald-400 transition-colors">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/10"><Mail size={18} /></span>
                  hello@evergreen.ai
                </a>
                <div className="flex items-center gap-3 text-[15px]">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/10"><MessageCircle size={18} /></span>
                  @evergreen
                </div>
              </div>
              <p className="mt-7 text-sm text-white/45">Отвечаем в течение рабочего дня.</p>
            </div>
          </Reveal>
        </div>
      </div>
    </div>
  );
}
