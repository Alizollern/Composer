import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthProvider";

export const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-paper text-ink">
        <div className="animate-pulse-soft">Загрузка Evergreen...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Если нужны конкретные роли (например ["manager", "owner"])
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="flex items-center justify-center h-screen bg-paper text-ink">
        <div className="text-center">
          <h2 className="text-2xl font-serif text-forest mb-2">Нет доступа</h2>
          <p>У вашей роли ({user.role}) нет прав для просмотра этой страницы.</p>
        </div>
      </div>
    );
  }

  return children;
};
