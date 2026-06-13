import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, Bot, Shield, Zap, Sparkles, Network, Dumbbell, Coffee, Scissors, ShoppingBag, Stethoscope, Car, Pill, UtensilsCrossed, Star } from "lucide-react";
import { useLanguage } from "../app/LanguageContext";

// Сети, которые «нам доверяют» (демо-данные для соцпруфа)
const CLIENTS = [
  { name: "Bronx Fitness", icon: Dumbbell },
  { name: "Dala Burger", icon: UtensilsCrossed },
  { name: "Bahyt Coffee", icon: Coffee },
  { name: "Tumar Beauty", icon: Scissors },
  { name: "Altyn Market", icon: ShoppingBag },
  { name: "Zerde Dental", icon: Stethoscope },
  { name: "Nomad Auto", icon: Car },
  { name: "Samal Pharm", icon: Pill },
];

const TESTIMONIALS = [
  {
    quote: "Скрипты и стандарты больше не лежат мёртвым грузом в Google Docs. Команда реально ими пользуется прямо на смене.",
    name: "Арман Сейтказы",
    role: "Управляющий сетью, Dala Burger",
  },
  {
    quote: "Вижу, какие вопросы повторяются — и сразу понимаю, где у нас дыры в регламентах. Это бесценно для роста сети.",
    name: "Динара Каримова",
    role: "Основатель, Tumar Beauty",
  },
];

export default function Landing() {
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0, 1], [0, 200]);
  const { t } = useLanguage();

  return (
    <div className="relative w-full bg-[#fafafa] overflow-hidden">
      
      {/* Animated Background Gradients */}
      <div className="absolute top-0 left-0 w-full h-screen overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-brand-400/20 rounded-full mix-blend-multiply filter blur-[100px] animate-blob"></div>
        <div className="absolute top-[20%] right-[-10%] w-[40%] h-[40%] bg-blue-400/20 rounded-full mix-blend-multiply filter blur-[100px] animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-[-20%] left-[20%] w-[40%] h-[40%] bg-purple-400/20 rounded-full mix-blend-multiply filter blur-[100px] animate-blob animation-delay-4000"></div>
        <div className="absolute inset-0 bg-dot-pattern opacity-50"></div>
      </div>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 md:pt-48 md:pb-32 px-6 max-w-7xl mx-auto">
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="text-center max-w-4xl mx-auto"
        >
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white border border-slate-200 shadow-sm mb-8">
            <Sparkles size={14} className="text-brand-600" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">{t('eyebrow')}</span>
          </div>
          
          <h1 className="text-6xl md:text-8xl font-extrabold text-slate-900 tracking-tighter mb-8 leading-[1.1]">
            {t('heroTitle1')} <br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-blue-600">
              {t('heroTitle2')}
            </span>
          </h1>
          
          <p className="text-xl text-slate-600 mb-10 max-w-2xl mx-auto leading-relaxed">
            {t('heroDesc')}
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/register" className="btn btn-primary px-8 py-4 text-lg w-full sm:w-auto group">
              {t('startFreeTrial')} 
              <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link to="/login" className="btn btn-secondary px-8 py-4 text-lg w-full sm:w-auto">
              {t('viewDemo')}
            </Link>
          </div>
        </motion.div>

        {/* Visual Product Representation */}
        <motion.div 
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.3, ease: "easeOut" }}
          style={{ y }}
          className="mt-20 relative max-w-5xl mx-auto"
        >
          <div className="spotlight-card p-2 md:p-4 shadow-2xl shadow-brand-900/10">
            <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
              <div className="flex items-center px-4 py-3 border-b border-slate-100 bg-slate-50/50">
                <div className="flex space-x-2">
                  <div className="w-3 h-3 rounded-full bg-red-400/80"></div>
                  <div className="w-3 h-3 rounded-full bg-amber-400/80"></div>
                  <div className="w-3 h-3 rounded-full bg-green-400/80"></div>
                </div>
                <div className="mx-auto text-xs font-medium text-slate-400">Evergreen Chat</div>
              </div>

              <div className="p-6 md:p-10 bg-white relative">
                 <div className="absolute inset-0 bg-dot-pattern opacity-[0.03]"></div>
                 <div className="space-y-6 relative z-10">
                   <div className="flex items-start max-w-2xl ml-auto justify-end">
                     <div className="bg-slate-900 text-white px-5 py-3 rounded-2xl rounded-tr-sm text-sm">
                       Клиент хочет заморозить абонемент на месяц. Что делать?
                     </div>
                   </div>
                   <div className="flex items-start max-w-2xl">
                     <div className="w-8 h-8 rounded-lg bg-brand-100 text-brand-600 flex items-center justify-center mr-4 shrink-0 mt-1">
                       <Bot size={18} />
                     </div>
                     <div>
                       <div className="bg-white border border-slate-200 shadow-sm px-5 py-4 rounded-2xl rounded-tl-sm text-sm text-slate-700 leading-relaxed">
                         Заморозка доступна на срок от 7 до 30 дней при действующем абонементе. Оформите её в CRM через раздел «Абонемент → Пауза» и зафиксируйте причину со слов клиента. Платные карты можно замораживать один раз за период действия.
                         <div className="mt-3 pt-3 border-t border-slate-100 flex items-center gap-2">
                           <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Источник:</span>
                           <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded border border-slate-200">Стандарты_администратора.pdf</span>
                         </div>
                       </div>
                     </div>
                   </div>
                 </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Integrations Band */}
      <section className="py-10 border-y border-slate-200 bg-white overflow-hidden relative">
        <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-white to-transparent z-10"></div>
        <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-white to-transparent z-10"></div>
        <div className="max-w-7xl mx-auto px-6 text-center mb-6">
          <p className="text-sm font-semibold uppercase tracking-widest text-slate-400">{t('integrationsTitle')}</p>
        </div>
        <div className="flex w-max animate-[shimmer_20s_linear_infinite] opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
          {[...CLIENTS, ...CLIENTS].map((c, i) => (
            <div key={i} className="px-12 flex items-center space-x-2 text-2xl font-bold text-slate-800 whitespace-nowrap">
              <c.icon size={26} className="text-slate-400" />
              <span>{c.name}</span>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works Timeline */}
      <section className="py-32 relative bg-white">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight">{t('howItWorksTitle')}</h2>
          </div>
          
          <div className="relative border-l-2 border-slate-200 ml-6 md:ml-1/2 space-y-20">
            {[
              { num: 1, title: t('step1Title'), desc: t('step1Desc'), delay: 0 },
              { num: 2, title: t('step2Title'), desc: t('step2Desc'), delay: 0.2 },
              { num: 3, title: t('step3Title'), desc: t('step3Desc'), delay: 0.4 },
            ].map((step, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.6, delay: step.delay }}
                className="relative pl-12"
              >
                <div className="absolute -left-[17px] top-0 w-8 h-8 bg-brand-100 border-4 border-white rounded-full flex items-center justify-center text-brand-600 font-bold text-sm">
                  {step.num}
                </div>
                <div className="bg-[#fafafa] p-8 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
                  <h3 className="text-2xl font-bold text-slate-900 mb-3">{step.title}</h3>
                  <p className="text-slate-600 leading-relaxed text-lg">{step.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Feature Section (Bento Grid) */}
      <section className="py-32 relative z-10 bg-slate-50 border-t border-slate-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight">{t('featuresTitle')}</h2>
            <p className="mt-4 text-xl text-slate-600">{t('featuresSubtitle')}</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <BentoCard 
              icon={<Zap className="text-amber-500" />}
              title={t('feat1Title')}
              desc={t('feat1Desc')}
              delay={0.1}
            />
            <BentoCard 
              icon={<Shield className="text-brand-500" />}
              title={t('feat2Title')}
              desc={t('feat2Desc')}
              delay={0.2}
            />
            <BentoCard 
              icon={<Network className="text-blue-500" />}
              title={t('feat3Title')}
              desc={t('feat3Desc')}
              delay={0.3}
            />
          </div>
        </div>
      </section>
      
      {/* Testimonials */}
      <section className="py-32 relative bg-white border-t border-slate-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight">Сети уже работают на Evergreen</h2>
            <p className="mt-4 text-xl text-slate-600">Меньше хаоса на смене, единый стандарт в каждой точке.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {TESTIMONIALS.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.6, delay: i * 0.1 }}
                className="bg-[#fafafa] p-8 rounded-2xl border border-slate-200 shadow-sm flex flex-col h-full"
              >
                <div className="flex gap-1 mb-5 text-amber-400">
                  {[1,2,3,4,5].map((s) => <Star key={s} size={16} fill="currentColor" />)}
                </div>
                <p className="text-slate-700 leading-relaxed text-lg flex-1">«{item.quote}»</p>
                <div className="mt-6 pt-6 border-t border-slate-200">
                  <div className="font-bold text-slate-900">{item.name}</div>
                  <div className="text-sm text-slate-500">{item.role}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 relative overflow-hidden border-t border-slate-200">
        <div className="absolute inset-0 bg-slate-900">
           <div className="absolute inset-0 bg-dot-pattern opacity-10"></div>
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">{t('ctaTitle')}</h2>
          <p className="text-xl text-slate-300 mb-10">{t('ctaDesc')}</p>
          <Link to="/register" className="inline-flex items-center justify-center px-8 py-4 bg-white text-slate-900 font-bold rounded-full hover:bg-slate-100 transition-all shadow-[0_0_40px_rgba(255,255,255,0.2)] hover:shadow-[0_0_60px_rgba(255,255,255,0.3)] hover:-translate-y-1">
            {t('ctaButton')}
          </Link>
        </div>
      </section>

    </div>
  );
}

// Interactive Hover Card Component
function BentoCard({ icon, title, desc, delay }) {
  const divRef = useRef(null);
  const [isFocused, setIsFocused] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [opacity, setOpacity] = useState(0);

  const handleMouseMove = (e) => {
    if (!divRef.current || isFocused) return;
    const div = divRef.current;
    const rect = div.getBoundingClientRect();
    setPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleFocus = () => {
    setIsFocused(true);
    setOpacity(1);
  };

  const handleBlur = () => {
    setIsFocused(false);
    setOpacity(0);
  };

  const handleMouseEnter = () => setOpacity(1);
  const handleMouseLeave = () => setOpacity(0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ duration: 0.6, delay }}
      ref={divRef}
      onMouseMove={handleMouseMove}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="relative spotlight-card p-8 group cursor-pointer h-full"
    >
      {/* Hover Spotlight */}
      <div
        className="pointer-events-none absolute -inset-px rounded-3xl opacity-0 transition duration-300 group-hover:opacity-100 z-20"
        style={{
          opacity,
          background: `radial-gradient(600px circle at ${position.x}px ${position.y}px, rgba(124, 58, 237, 0.1), transparent 40%)`,
        }}
      />
      
      <div className="relative z-10">
        <div className="w-12 h-12 rounded-xl bg-white shadow-sm border border-slate-100 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
          {icon}
        </div>
        <h3 className="text-xl font-bold text-slate-900 mb-3">{title}</h3>
        <p className="text-slate-600 leading-relaxed text-sm">{desc}</p>
      </div>
    </motion.div>
  );
}
