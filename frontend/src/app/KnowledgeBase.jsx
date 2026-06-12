import React, { useState, useEffect } from "react";
import { useAuth } from "./AuthProvider";
import { api } from "../lib/api";
import { FileText, UploadCloud, Eye, Download, Users, Lock, Hexagon } from "lucide-react";

const STATUS_LABELS = { published: "Опубликован", draft: "Черновик", archived: "Архив" };

export default function KnowledgeBase() {
  const { user } = useAuth();
  const isManager = user?.role === "manager" || user?.role === "owner";
  
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("published"); 
  
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const docs = await api.documents.list(filter);
      setDocuments(docs);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [filter]);

  const handleDownload = async (id, title) => {
    try {
      const blob = await api.documents.downloadOriginal(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = title || "document.txt";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      console.error("Download failed", e);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 space-y-4 md:space-y-0">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">База знаний</h1>
          <p className="text-slate-500 mt-1">
            {isManager ? "Управляйте стандартами и регламентами компании." : "Изучайте задокументированные стандарты вашей компании."}
          </p>
        </div>
        
        {isManager && (
          <div className="flex items-center space-x-3">
            <button 
              onClick={() => setIsUploadOpen(true)}
              className="btn btn-primary"
            >
              <UploadCloud size={18} className="mr-2" />
              <span>Загрузить документ</span>
            </button>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-4 mb-6 border-b border-slate-200 pb-4">
        <div className="flex space-x-2">
          {[
            { id: "published", label: "Опубликованные" },
            { id: "draft", label: "Черновики", roles: ["manager", "owner"] },
            { id: "archived", label: "Архив", roles: ["manager", "owner"] },
          ].map((tab) => {
            if (tab.roles && !tab.roles.includes(user?.role)) return null;
            return (
              <button
                key={tab.id}
                onClick={() => setFilter(tab.id)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  filter === tab.id 
                    ? "bg-slate-800 text-white" 
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1,2,3].map(i => (
            <div key={i} className="bg-white rounded-lg p-6 h-40 border border-slate-200 animate-pulse" />
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="bg-white rounded-lg border border-slate-200 border-dashed p-12 text-center flex flex-col items-center">
          <Hexagon size={48} className="text-slate-300 mb-4" />
          <h3 className="text-lg font-bold text-slate-900 mb-2">Документов не найдено</h3>
          <p className="text-slate-500">В этой категории пока нет стандартов.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {documents.map(doc => (
            <div key={doc.id} className="bg-white rounded-lg p-6 border border-slate-200 shadow-sm flex flex-col hover:border-brand-300 transition-colors">
              <div className="flex items-start justify-between mb-4">
                <div className="p-2 bg-brand-50 rounded text-brand-600">
                  <FileText size={20} />
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium border ${
                    doc.status === "published" ? "bg-green-50 text-green-700 border-green-200" :
                    doc.status === "draft" ? "bg-amber-50 text-amber-700 border-amber-200" :
                    "bg-slate-50 text-slate-600 border-slate-200"
                  }`}>
                    {STATUS_LABELS[doc.status] || doc.status}
                  </span>
                </div>
              </div>
              
              <h3 className="text-base font-bold text-slate-900 mb-1 line-clamp-2">{doc.title}</h3>
              {doc.category && <p className="text-sm text-slate-500 mb-4">{doc.category}</p>}
              
              <div className="mt-auto pt-4 flex items-center justify-between border-t border-slate-100">
                <div className="flex items-center text-slate-500 text-xs">
                  {doc.audience_roles && doc.audience_roles.length > 0 ? (
                    <div className="flex items-center" title="Ограниченный доступ">
                      <Lock size={12} className="mr-1" />
                      <span>Ограничен</span>
                    </div>
                  ) : (
                    <div className="flex items-center" title="Доступно всем">
                      <Users size={12} className="mr-1" />
                      <span>Все</span>
                    </div>
                  )}
                </div>
                
                <div className="flex space-x-1">
                  <button className="p-1.5 text-slate-400 hover:text-brand-600 rounded hover:bg-brand-50" title="Читать">
                    <Eye size={16} />
                  </button>
                  <button
                    onClick={() => handleDownload(doc.id, doc.title)}
                    className="p-1.5 text-slate-400 hover:text-brand-600 rounded hover:bg-brand-50" title="Скачать оригинал"
                  >
                    <Download size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {isUploadOpen && (
        <UploadModal onClose={() => setIsUploadOpen(false)} onUploadSuccess={fetchDocuments} />
      )}
    </div>
  );
}

function UploadModal({ onClose, onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    try {
      await api.documents.upload(file, "general");
      onUploadSuccess();
      onClose();
    } catch (e) {
      alert("Ошибка: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-lg">
        <h2 className="text-xl font-bold text-slate-900 mb-4">Загрузить документ</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input 
            type="file" 
            onChange={(e) => setFile(e.target.files[0])}
            className="w-full text-sm text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
          />
          <div className="flex justify-end space-x-3 pt-4">
            <button type="button" onClick={onClose} className="btn btn-secondary">Отмена</button>
            <button type="submit" disabled={loading || !file} className="btn btn-primary">
              {loading ? "Загрузка..." : "Загрузить"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
