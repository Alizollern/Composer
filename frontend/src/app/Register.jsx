import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "./AuthProvider";

export default function Register() {
  const [formData, setFormData] = useState({ 
    company_name: "", 
    slug: "", 
    owner_name: "", 
    owner_email: "", 
    owner_password: "" 
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const validateSlug = (slug) => /^[a-z0-9][a-z0-9\-]{1,62}$/.test(slug);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!validateSlug(formData.slug)) {
      setError("Slug должен состоять только из маленьких латинских букв, цифр и дефисов.");
      return;
    }
    if (formData.owner_password.length < 6) {
      setError("Пароль должен быть не менее 6 символов.");
      return;
    }

    setLoading(true);
    try {
      await register(formData);
      navigate("/app");
    } catch (err) {
      setError(err.message || "Ошибка регистрации");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#fafafa] flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg border border-slate-100 p-8 animate-fade-in-up">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Evergreen</h1>
          <p className="text-slate-500 mt-2">Регистрация компании</p>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-100">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Название компании</label>
            <input
              type="text"
              required
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Кофейня Зёрна"
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">ID Компании (slug)</label>
            <input
              type="text"
              required
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="zerna-coffee"
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase() })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1">Ваше имя</label>
              <input
                type="text"
                required
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="Иван"
                value={formData.owner_name}
                onChange={(e) => setFormData({ ...formData, owner_name: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input
              type="email"
              required
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="owner@company.com"
              value={formData.owner_email}
              onChange={(e) => setFormData({ ...formData, owner_email: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Пароль</label>
            <input
              type="password"
              required
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="••••••••"
              value={formData.owner_password}
              onChange={(e) => setFormData({ ...formData, owner_password: e.target.value })}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full py-3 rounded-lg disabled:opacity-50"
          >
            {loading ? "Регистрация..." : "Создать компанию"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Уже есть аккаунт?{" "}
          <Link to="/login" className="text-brand-600 font-medium hover:underline">
            Войти
          </Link>
        </p>
      </div>
    </div>
  );
}
