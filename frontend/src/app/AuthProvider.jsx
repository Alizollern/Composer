import React, { createContext, useContext, useState, useEffect } from "react";
import { api, setToken, clearToken } from "../lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const userData = await api.auth.me();
        setUser(userData);
      } catch (err) {
        setUser(null);
        clearToken();
      } finally {
        setLoading(false);
      }
    };
    
    checkAuth();

    // Слушаем глобальное событие разлогина из api.js
    const handleUnauthorized = () => {
      setUser(null);
    };
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    
    return () => {
      window.removeEventListener("auth:unauthorized", handleUnauthorized);
    };
  }, []);

  const login = async (credentials) => {
    const res = await api.auth.login(credentials);
    setToken(res.access_token);
    const userData = await api.auth.me();
    setUser(userData);
  };

  const register = async (data) => {
    const res = await api.auth.registerCompany(data);
    setToken(res.access_token);
    const userData = await api.auth.me();
    setUser(userData);
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
