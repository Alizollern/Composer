import React from "react";
import { Check } from "lucide-react";
import { Link } from "react-router-dom";

export default function Pricing() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
      <div className="text-center mb-16">
        <h1 className="text-4xl font-extrabold text-slate-900 mb-4">Простые и понятные тарифы</h1>
        <p className="text-xl text-slate-600">Без скрытых платежей. Отмена в любой момент.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
        {/* Старт */}
        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm flex flex-col">
          <h3 className="text-xl font-bold text-slate-900 mb-2">Старт</h3>
          <p className="text-slate-500 mb-6">Для одной точки и небольшой команды.</p>
          <div className="mb-6">
            <span className="text-4xl font-extrabold text-slate-900">25 000 ₸</span>
            <span className="text-slate-500">/мес</span>
          </div>
          <Link to="/register" className="btn btn-secondary w-full mb-8">Начать</Link>
          <ul className="space-y-4 flex-1">
            <PricingFeature text="До 10 сотрудников" />
            <PricingFeature text="До 100 документов" />
            <PricingFeature text="Чат по стандартам" />
            <PricingFeature text="Базовая аналитика вопросов" />
          </ul>
        </div>

        {/* Сеть */}
        <div className="bg-white border-2 border-brand-600 rounded-2xl p-8 shadow-md relative flex flex-col">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-brand-600 text-white px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide">
            Популярный
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Сеть</h3>
          <p className="text-slate-500 mb-6">Для растущей сети с несколькими точками.</p>
          <div className="mb-6">
            <span className="text-4xl font-extrabold text-slate-900">90 000 ₸</span>
            <span className="text-slate-500">/мес</span>
          </div>
          <Link to="/register" className="btn btn-primary w-full mb-8">Начать</Link>
          <ul className="space-y-4 flex-1">
            <PricingFeature text="До 50 сотрудников" />
            <PricingFeature text="Без лимита по документам" />
            <PricingFeature text="Онбординг и тесты для новичков" />
            <PricingFeature text="Карта пробелов в знаниях" />
            <PricingFeature text="Доступ по ролям и точкам" />
          </ul>
        </div>

        {/* Корпоративный */}
        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm flex flex-col">
          <h3 className="text-xl font-bold text-slate-900 mb-2">Корпоративный</h3>
          <p className="text-slate-500 mb-6">Для крупных сетей и франшиз.</p>
          <div className="mb-6">
            <span className="text-4xl font-extrabold text-slate-900">Индивидуально</span>
          </div>
          <a href="mailto:hello@evergreen.kz" className="btn btn-secondary w-full mb-8">Связаться с нами</a>
          <ul className="space-y-4 flex-1">
            <PricingFeature text="Без лимита по сотрудникам" />
            <PricingFeature text="Сбор отзывов из мессенджеров" />
            <PricingFeature text="Персональный менеджер" />
            <PricingFeature text="Интеграции с вашими системами" />
            <PricingFeature text="Приоритетная поддержка" />
          </ul>
        </div>
      </div>
    </div>
  );
}

function PricingFeature({ text }) {
  return (
    <li className="flex items-start">
      <Check className="h-5 w-5 text-brand-600 mr-3 flex-shrink-0" />
      <span className="text-slate-600 text-sm">{text}</span>
    </li>
  );
}
