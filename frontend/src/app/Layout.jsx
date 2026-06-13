import React, { useState } from "react";
import { Outlet, NavLink } from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { MessageSquare, BookOpen, GraduationCap, Map, Users, LogOut, Menu, X, Hexagon, ScrollText, Gauge, Sparkles } from "lucide-react";

export default function Layout() {
  const { user, logout } = useAuth();
  const [isSidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => setSidebarOpen(!isSidebarOpen);

  const getNavItems = () => {
    const items = [
      { path: "/app/chat", label: "Ассистент", icon: MessageSquare, roles: ["employee", "manager", "owner"] },
      { path: "/app/knowledge", label: "База знаний", icon: BookOpen, roles: ["employee", "manager", "owner"] },
      { path: "/app/learning", label: "Обучение", icon: GraduationCap, roles: ["employee", "manager", "owner"] },
      { path: "/app/command-center", label: "Командный центр", icon: Gauge, roles: ["manager", "owner"] },
      { path: "/app/advisor", label: "Опер-дир", icon: Sparkles, roles: ["manager", "owner"] },
      { path: "/app/assistant-log", label: "Журнал ассистента", icon: ScrollText, roles: ["owner"] },
      // Страницы ниже пока не реализованы во фронте — вернуть, когда появятся роуты:
      // { path: "/app/tracks", label: "Треки", icon: Map, roles: ["manager", "owner"] },
      // { path: "/app/team", label: "Команда", icon: Users, roles: ["manager", "owner"] },
    ];
    return items.filter(item => item.roles.includes(user?.role));
  };

  const navItems = getNavItems();

  return (
    <div className="flex h-screen bg-slate-50 font-sans overflow-hidden text-slate-900">
      
      {/* Mobile sidebar backdrop */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-slate-900/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar - Standard SaaS */}
      <aside className={`
        fixed md:static inset-y-0 left-0 z-50
        w-64 bg-white border-r border-slate-200 flex flex-col
        transition-transform duration-300 ease-in-out
        ${isSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
      `}>
        <div className="flex items-center justify-between p-4 border-b border-slate-200 h-16">
          <div className="flex items-center space-x-2">
            <Hexagon className="h-6 w-6 text-brand-600" fill="currentColor" strokeWidth={1} />
            <span className="font-bold text-lg tracking-tight">Evergreen</span>
          </div>
          <button className="md:hidden text-slate-500 hover:text-slate-900" onClick={toggleSidebar}>
            <X size={24} />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) => `
                flex items-center space-x-3 px-3 py-2 rounded-md transition-colors text-sm font-medium
                ${isActive 
                  ? "bg-brand-50 text-brand-700" 
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }
              `}
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-200 bg-slate-50/50">
          <div className="flex flex-col mb-4">
            <span className="text-sm font-semibold text-slate-900 truncate">{user?.email || "User"}</span>
            <span className="text-xs text-slate-500 capitalize">{user?.role}</span>
          </div>
          <button 
            onClick={logout}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-md transition-colors text-sm font-medium"
          >
            <LogOut size={16} />
            <span>Выйти</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative bg-slate-50">
        {/* Mobile Header */}
        <header className="md:hidden flex items-center p-4 bg-white border-b border-slate-200 z-30 h-16">
          <button onClick={toggleSidebar} className="text-slate-600 mr-4">
            <Menu size={24} />
          </button>
          <span className="font-bold text-lg text-slate-900">Evergreen</span>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
