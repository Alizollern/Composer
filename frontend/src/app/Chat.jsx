import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, FileText, ChevronRight } from "lucide-react";
import { api } from "../lib/api";

export default function Chat() {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content: "Здравствуйте! Я ассистент Evergreen. Отвечаю на вопросы строго по стандартам и регламентам вашей компании. Чем могу помочь?",
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = { id: Date.now().toString(), role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.chat.ask(userMessage.content);
      
      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.refused
          ? "Не нашёл ответа на этот вопрос в текущих документах. Я зафиксировал этот пробел — руководство его увидит."
          : res.answer,
        sources: res.sources,
        refused: res.refused,
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (e) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Ошибка сети. Попробуйте ещё раз.",
        isError: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
      
      <div className="px-6 py-4 border-b border-slate-200 bg-white">
        <h2 className="text-lg font-bold text-slate-900">Ассистент компании</h2>
        <p className="text-sm text-slate-500">Отвечает строго на основе загруженных документов.</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`flex max-w-[80%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
              <div className={`flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center mt-1
                ${msg.role === "user" ? "bg-slate-800 ml-3 text-white" : "bg-brand-100 mr-3 text-brand-600"}
              `}>
                {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
              </div>
              
              <div className="flex flex-col">
                <div className={`p-4 rounded-lg shadow-sm ${
                  msg.role === "user" 
                    ? "bg-white border border-slate-200 text-slate-900" 
                    : msg.isError 
                      ? "bg-red-50 text-red-800 border border-red-200"
                      : msg.refused
                        ? "bg-amber-50 text-amber-800 border border-amber-200"
                        : "bg-white border border-slate-200 text-slate-900"
                }`}>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</div>
                </div>

                {msg.sources && msg.sources.length > 0 && !msg.refused && (
                  <div className="mt-2 space-y-1">
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider ml-1">Источники:</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {msg.sources.map((src, i) => (
                        <div 
                          key={i} 
                          className="flex items-center text-xs bg-white border border-slate-200 text-slate-600 px-2 py-1 rounded hover:border-brand-300 hover:text-brand-600 transition-colors cursor-pointer"
                        >
                          <FileText size={12} className="mr-1.5" />
                          <span className="truncate max-w-[150px]">{src.document_title}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="flex max-w-[80%] flex-row">
              <div className="flex-shrink-0 w-8 h-8 rounded-md bg-brand-100 mr-3 text-brand-600 flex items-center justify-center mt-1">
                <Bot size={16} />
              </div>
              <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-sm flex items-center space-x-2 h-12">
                <div className="w-2 h-2 rounded-full bg-slate-300 animate-pulse"></div>
                <div className="w-2 h-2 rounded-full bg-slate-300 animate-pulse delay-75"></div>
                <div className="w-2 h-2 rounded-full bg-slate-300 animate-pulse delay-150"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white border-t border-slate-200">
        <form onSubmit={handleSubmit} className="flex items-center space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Задайте вопрос..."
            className="flex-1 px-4 py-2 bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="btn btn-primary px-4 py-2 h-full"
          >
            <Send size={18} className="mr-2" /> Отправить
          </button>
        </form>
      </div>
    </div>
  );
}
