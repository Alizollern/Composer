import React, { createContext, useState, useContext } from 'react';

const translations = {
  ru: {
    // Navigation
    features: "Возможности",
    pricing: "Тарифы",
    about: "О нас",
    login: "Войти",
    getStarted: "Начать работу",

    // Hero
    eyebrow: "Цифровой двойник руководителя",
    heroTitle1: "Стандарты вашей сети —",
    heroTitle2: "в голове каждого сотрудника.",
    heroDesc: "Загрузите регламенты, скрипты и стандарты. Evergreen превращает их в ассистента, который отвечает сотрудникам строго по вашим документам — и показывает, чего команда ещё не знает.",
    startFreeTrial: "Попробовать бесплатно",
    viewDemo: "Смотреть демо",

    // Clients band
    integrationsTitle: "Нам доверяют сети по всему Казахстану",

    // How It Works
    howItWorksTitle: "Как это работает",
    step1Title: "1. Загрузите свои стандарты",
    step1Desc: "Перетащите регламенты, скрипты продаж и инструкции — PDF, Word или текст. Всё хранится безопасно.",
    step2Title: "2. Evergreen всё запоминает",
    step2Desc: "Система разбирает каждый пункт ваших документов. Ни одна деталь не теряется.",
    step3Title: "3. Команда получает ответы",
    step3Desc: "Сотрудник спрашивает в чате и за секунду получает точный ответ со ссылкой на ваш документ. Если ответа в стандартах нет — система честно об этом скажет.",

    // Bento Features
    featuresTitle: "Всё, чтобы держать сеть в едином стандарте.",
    featuresSubtitle: "Технологии корпоративного уровня — в простом и понятном интерфейсе.",
    feat1Title: "Ответы за секунду",
    feat1Desc: "Новичок находит ответ быстрее, чем успел бы позвонить управляющему. Меньше звонков, меньше ошибок на смене.",
    feat2Title: "Только по вашим документам",
    feat2Desc: "Если ответа нет в ваших стандартах — система так и скажет. Никаких выдумок: сотрудник получает правило, а не фантазию.",
    feat3Title: "Видно, чего команда не знает",
    feat3Desc: "Вы видите, что чаще всего спрашивают и где в стандартах пробелы. Дорабатываете — и сеть становится сильнее.",

    // CTA
    ctaTitle: "Хватит объяснять одно и то же каждому новичку.",
    ctaDesc: "Подключите Evergreen и дайте команде доступ ко всем стандартам компании — в одном чате.",
    ctaButton: "Начать бесплатно"
  },
  en: {
    // Navigation
    features: "Features",
    pricing: "Pricing",
    about: "About",
    login: "Sign in",
    getStarted: "Get Started",

    // Hero
    eyebrow: "A digital twin of the owner",
    heroTitle1: "Your chain's standards —",
    heroTitle2: "in every employee's head.",
    heroDesc: "Upload your procedures, scripts and standards. Evergreen turns them into an assistant that answers your team strictly from your documents — and shows you what they still don't know.",
    startFreeTrial: "Start Free Trial",
    viewDemo: "View Live Demo",

    // Clients band
    integrationsTitle: "Trusted by growing chains across Kazakhstan",

    // How It Works
    howItWorksTitle: "How it works",
    step1Title: "1. Upload your standards",
    step1Desc: "Drag and drop your procedures, sales scripts and manuals — PDF, Word or text. Everything is stored securely.",
    step2Title: "2. Evergreen remembers everything",
    step2Desc: "The system breaks down every point of your documents. Not a single detail gets lost.",
    step3Title: "3. Your team gets answers",
    step3Desc: "An employee asks in chat and gets a precise answer in seconds, with a citation to your document. If it isn't in your standards, the system says so honestly.",

    // Bento Features
    featuresTitle: "Everything to keep your chain on one standard.",
    featuresSubtitle: "Enterprise-grade technology in a simple, clear interface.",
    feat1Title: "Answers in a second",
    feat1Desc: "A new hire finds the answer faster than they could call the manager. Fewer calls, fewer mistakes on shift.",
    feat2Title: "Only from your documents",
    feat2Desc: "If it isn't in your standards, the system says so. No making things up — the employee gets a rule, not a fantasy.",
    feat3Title: "See what your team doesn't know",
    feat3Desc: "You see what gets asked most and where your standards have gaps. Fix them, and the whole chain gets stronger.",

    // CTA
    ctaTitle: "Stop explaining the same thing to every new hire.",
    ctaDesc: "Plug in Evergreen and give your team access to every company standard — in a single chat.",
    ctaButton: "Get Started for Free"
  },
  kz: {
    // Navigation
    features: "Мүмкіндіктер",
    pricing: "Тарифтер",
    about: "Біз туралы",
    login: "Кіру",
    getStarted: "Бастау",

    // Hero
    eyebrow: "Басшының цифрлық егізі",
    heroTitle1: "Желіңіздің стандарттары —",
    heroTitle2: "әр қызметкердің есінде.",
    heroDesc: "Регламенттер, скрипттер мен стандарттарды жүктеңіз. Evergreen оларды қызметкерлерге тек сіздің құжаттарыңыз бойынша жауап беретін көмекшіге айналдырады — әрі команда нені әлі білмейтінін көрсетеді.",
    startFreeTrial: "Тегін байқап көру",
    viewDemo: "Демонстрацияны көру",

    // Clients band
    integrationsTitle: "Бізге Қазақстандағы желілер сенеді",

    // How It Works
    howItWorksTitle: "Бұл қалай жұмыс істейді",
    step1Title: "1. Стандарттарыңызды жүктеңіз",
    step1Desc: "Регламенттер, сату скрипттері мен нұсқаулықтарды сүйреп апарыңыз — PDF, Word немесе мәтін. Бәрі қауіпсіз сақталады.",
    step2Title: "2. Evergreen бәрін есте сақтайды",
    step2Desc: "Жүйе құжаттарыңыздың әр тармағын талдайды. Бірде-бір бөлшек жоғалмайды.",
    step3Title: "3. Команда жауап алады",
    step3Desc: "Қызметкер чатта сұрайды да, бірнеше секундта құжатыңызға сілтемесі бар нақты жауап алады. Егер стандартта жауап болмаса — жүйе оны адал айтады.",

    // Bento Features
    featuresTitle: "Желіні бірыңғай стандартта ұстауға керектің бәрі.",
    featuresSubtitle: "Корпоративтік деңгейдегі технология — қарапайым әрі түсінікті интерфейсте.",
    feat1Title: "Бір секундта жауап",
    feat1Desc: "Жаңа қызметкер басшыға қоңырау шалғаннан тез жауап табады. Қоңырау азаяды, ауысымдағы қателер кемиді.",
    feat2Title: "Тек сіздің құжаттарыңыз бойынша",
    feat2Desc: "Егер стандартта жауап болмаса — жүйе солай дейді. Ойдан шығару жоқ: қызметкер қиял емес, ереже алады.",
    feat3Title: "Команда нені білмейтіні көрінеді",
    feat3Desc: "Не жиі сұралатынын және стандартта қай жерде олқылық бар екенін көресіз. Түзетесіз — бүкіл желі күшейеді.",

    // CTA
    ctaTitle: "Әр жаңа қызметкерге бір нәрсені қайталауды доғарыңыз.",
    ctaDesc: "Evergreen-ді қосып, командаңызға компанияның барлық стандарттарын бір чатта ашыңыз.",
    ctaButton: "Тегін бастау"
  }
};

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState('ru');

  const t = (key) => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
