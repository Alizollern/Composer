import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";

import { AuthProvider } from "./app/AuthProvider";
import { LanguageProvider } from "./app/LanguageContext";
import { ProtectedRoute } from "./app/ProtectedRoute";

// Marketing
import SiteLayout from "./components/SiteLayout.jsx";
import Landing from "./pages/Landing.jsx";
import Features from "./pages/Features.jsx";
import Pricing from "./pages/Pricing.jsx";
import About from "./pages/About.jsx";

// Auth
import Login from "./app/Login.jsx";
import Register from "./app/Register.jsx";

// App
import Layout from "./app/Layout.jsx";
import Chat from "./app/Chat.jsx";
import KnowledgeBase from "./app/KnowledgeBase.jsx";
import Learning from "./app/Learning.jsx";
import CommandCenter from "./app/CommandCenter.jsx";
import CoAuthor from "./app/CoAuthor.jsx";
import Digest from "./app/Digest.jsx";
import Advisor from "./app/Advisor.jsx";
import AssistantLog from "./app/AssistantLog.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AuthProvider>
      <LanguageProvider>
        <BrowserRouter>
          <Routes>
            {/* Marketing */}
            <Route element={<SiteLayout />}>
              <Route path="/" element={<Landing />} />
              <Route path="/features" element={<Features />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/about" element={<About />} />
            </Route>

            {/* Auth */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* App */}
            <Route 
              path="/app" 
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="chat" replace />} />
              <Route path="chat" element={<Chat />} />
              <Route path="knowledge" element={<KnowledgeBase />} />
              <Route path="learning" element={<Learning />} />
              <Route path="command-center" element={<CommandCenter />} />
              <Route path="coauthor" element={<CoAuthor />} />
              <Route path="digest" element={<Digest />} />
              <Route path="advisor" element={<Advisor />} />
              <Route path="assistant-log" element={<AssistantLog />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </LanguageProvider>
    </AuthProvider>
  </React.StrictMode>
);
