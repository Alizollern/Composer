import { Outlet, NavLink, Link } from "react-router-dom";
import Logo from "./Logo.jsx";

export default function SiteLayout() {
  return (
    <>
      <header className="site-header">
        <div className="container">
          <Link to="/" className="logo">
            <Logo />
            <span className="logo-name">Evergreen</span>
          </Link>
          <nav className="site-nav">
            <span className="links">
              <NavLink to="/features">Возможности</NavLink>
              <NavLink to="/pricing">Цены</NavLink>
              <NavLink to="/about">О нас</NavLink>
              <NavLink to="/contact">Контакты</NavLink>
            </span>
            <Link to="/app" className="btn btn-primary btn-sm cta">Открыть двойника</Link>
          </nav>
        </div>
      </header>

      <Outlet />

      <footer className="site-footer">
        <div className="container">
          <div className="footer-grid">
            <div>
              <Link to="/" className="logo">
                <Logo />
                <span className="logo-name">Evergreen</span>
              </Link>
              <p className="footer-about">
                Цифровой двойник руководителя. Поручайте операционную работу —
                двойник соберёт данные, проанализирует и подготовит готовый результат.
              </p>
            </div>
            <div className="footer-col">
              <h4>Продукт</h4>
              <Link to="/features">Возможности</Link>
              <Link to="/pricing">Цены</Link>
              <Link to="/app">Открыть двойника</Link>
            </div>
            <div className="footer-col">
              <h4>Компания</h4>
              <Link to="/about">О нас</Link>
              <Link to="/contact">Контакты</Link>
            </div>
          </div>
          <div className="footer-bottom">
            <span>© {new Date().getFullYear()} Evergreen. Все права защищены.</span>
            <span>Сделано для руководителей.</span>
          </div>
        </div>
      </footer>
    </>
  );
}
