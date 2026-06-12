import React from "react";
import { Outlet, Link } from "react-router-dom";
import { Sparkles, Globe } from "lucide-react";
import { useLanguage } from "../app/LanguageContext";

export default function SiteLayout() {
  const { language, setLanguage, t } = useLanguage();

  return (
    <div className="min-h-screen bg-[#fafafa] font-sans flex flex-col text-slate-900 selection:bg-brand-100 selection:text-brand-900">
      <header className="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-xl border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-8">
              <Link to="/" className="flex items-center space-x-2">
                <Sparkles className="h-6 w-6 text-brand-600" />
                <span className="font-bold text-xl tracking-tight text-slate-900">Evergreen</span>
              </Link>
              <nav className="hidden md:flex space-x-6">
                <Link to="/features" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">{t('features')}</Link>
                <Link to="/pricing" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">{t('pricing')}</Link>
                <Link to="/about" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">{t('about')}</Link>
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              
              {/* Language Switcher */}
              <div className="relative group flex items-center text-sm font-medium text-slate-600 hover:text-slate-900 cursor-pointer">
                <Globe size={16} className="mr-1.5" />
                <span className="uppercase">{language}</span>
                <div className="absolute top-full right-0 mt-2 w-32 bg-white border border-slate-200 rounded-xl shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all flex flex-col overflow-hidden">
                  <button onClick={() => setLanguage('ru')} className={`px-4 py-2 text-left hover:bg-slate-50 ${language === 'ru' ? 'text-brand-600 font-bold bg-brand-50' : 'text-slate-700'}`}>Русский</button>
                  <button onClick={() => setLanguage('kz')} className={`px-4 py-2 text-left hover:bg-slate-50 ${language === 'kz' ? 'text-brand-600 font-bold bg-brand-50' : 'text-slate-700'}`}>Қазақша</button>
                  <button onClick={() => setLanguage('en')} className={`px-4 py-2 text-left hover:bg-slate-50 ${language === 'en' ? 'text-brand-600 font-bold bg-brand-50' : 'text-slate-700'}`}>English</button>
                </div>
              </div>

              <div className="w-px h-5 bg-slate-200 mx-2 hidden md:block"></div>

              <Link to="/login" className="hidden md:block text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">{t('login')}</Link>
              <Link to="/register" className="btn btn-primary bg-slate-900">{t('getStarted')}</Link>
            </div>
          </div>
        </div>
      </header>
      
      <main className="flex-grow pt-16">
        <Outlet />
      </main>

      <footer className="bg-white border-t border-slate-200 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-slate-500 text-sm flex flex-col items-center">
          <Sparkles className="h-5 w-5 text-slate-300 mb-4" />
          <p>&copy; {new Date().getFullYear()} Evergreen Intelligence. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
