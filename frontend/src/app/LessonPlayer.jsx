import React, { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { splitIntoCards } from "../lib/cards";
import {
  X, ChevronLeft, ChevronRight, BookOpen, CheckCircle2, XCircle,
  Trophy, RotateCcw, Loader2, ClipboardCheck,
} from "lucide-react";

// Проигрыватель одного шага трека: стандарт превращается в карточки со свайпом,
// затем (если требуется) мини-тест карточками. Оценка — на сервере (submitStep).
export default function LessonPlayer({ enrollment, step, onClose, onCompleted }) {
  const [phase, setPhase] = useState("loading"); // loading|cards|quiz|result|error
  const [error, setError] = useState("");

  const [cards, setCards] = useState([]);
  const [ci, setCi] = useState(0);

  const [quiz, setQuiz] = useState([]);          // вопросы теста (без ответов)
  const [quizToken, setQuizToken] = useState(null); // токен серверной копии теста
  const [qi, setQi] = useState(0);
  const [answers, setAnswers] = useState([]);    // выбранный индекс на вопрос
  const [quizLoading, setQuizLoading] = useState(false);

  const [result, setResult] = useState(null);    // grade + passed
  const [submitting, setSubmitting] = useState(false);

  // 1) Загружаем текст стандарта и режем на карточки.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const doc = await api.documents.getContent(step.document_id);
        if (!alive) return;
        setCards(splitIntoCards(doc.title || step.title, doc.content));
        setPhase("cards");
      } catch (e) {
        if (alive) { setError(e.message || "Не удалось открыть урок"); setPhase("error"); }
      }
    })();
    return () => { alive = false; };
  }, [step.document_id, step.title]);

  // ----- Навигация по карточкам -----
  const nextCard = () => {
    if (ci < cards.length - 1) setCi(ci + 1);
    else finishReading();
  };
  const prevCard = () => { if (ci > 0) setCi(ci - 1); };

  async function finishReading() {
    if (!step.require_quiz) {
      await submit(null);   // шаг без теста — просто отмечаем прочтение
      return;
    }
    setQuizLoading(true);
    setError("");
    try {
      const q = await api.quiz.generate(step.document_id, step.num_questions || 5);
      setQuiz(q.questions || []);
      setQuizToken(q.quiz_token);
      setAnswers(new Array((q.questions || []).length).fill(-1));
      setQi(0);
      setPhase("quiz");
    } catch (e) {
      setError(e.message || "Не удалось собрать тест");
      setPhase("error");
    } finally {
      setQuizLoading(false);
    }
  }

  // ----- Тест -----
  const pickAnswer = (idx) => {
    const a = answers.slice();
    a[qi] = idx;
    setAnswers(a);
  };
  const nextQuestion = () => {
    if (qi < quiz.length - 1) setQi(qi + 1);
    else submit(answers);
  };

  async function submit(answersPayload) {
    setSubmitting(true);
    setError("");
    try {
      const res = await api.tracks.submitStep(enrollment.enrollment_id, step.id, {
        quiz_token: quizToken,
        answers: answersPayload,
      });
      setResult(res);
      setPhase("result");
    } catch (e) {
      setError(e.message || "Не удалось засчитать шаг");
      setPhase("error");
    } finally {
      setSubmitting(false);
    }
  }

  const restart = () => {
    setResult(null); setQuiz([]); setQuizToken(null); setAnswers([]); setQi(0); setCi(0);
    setPhase("cards");
  };

  // ----- Свайп пальцем (мобильный) -----
  const touch = useRef({ x: 0 });
  const onTouchStart = (e) => { touch.current.x = e.changedTouches[0].clientX; };
  const onTouchEnd = (e) => {
    const dx = e.changedTouches[0].clientX - touch.current.x;
    if (Math.abs(dx) < 50) return;
    if (phase === "cards") (dx < 0 ? nextCard() : prevCard());
  };

  // Стрелки клавиатуры на десктопе.
  useEffect(() => {
    const onKey = (e) => {
      if (phase !== "cards") return;
      if (e.key === "ArrowRight") nextCard();
      if (e.key === "ArrowLeft") prevCard();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="fixed inset-0 z-[60] bg-slate-900/60 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Шапка */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
          <div className="flex items-center space-x-2 min-w-0">
            <BookOpen size={18} className="text-brand-600 flex-shrink-0" />
            <span className="font-semibold text-slate-900 truncate">{step.title || "Урок"}</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X size={22} />
          </button>
        </div>

        {/* Тело */}
        <div
          className="flex-1 overflow-y-auto p-6"
          onTouchStart={onTouchStart}
          onTouchEnd={onTouchEnd}
        >
          {phase === "loading" && (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <Loader2 size={32} className="animate-spin mb-3" />
              <span>Готовим урок…</span>
            </div>
          )}

          {phase === "error" && (
            <div className="text-center py-10">
              <XCircle size={36} className="text-red-400 mx-auto mb-3" />
              <p className="text-slate-700 mb-4">{error}</p>
              <button onClick={onClose} className="btn btn-secondary">Закрыть</button>
            </div>
          )}

          {phase === "cards" && cards.length > 0 && (
            <div>
              {/* Точки прогресса */}
              <div className="flex items-center justify-center gap-1.5 mb-5">
                {cards.map((_, i) => (
                  <span key={i} className={`h-1.5 rounded-full transition-all ${
                    i === ci ? "w-6 bg-brand-600" : i < ci ? "w-1.5 bg-brand-300" : "w-1.5 bg-slate-200"
                  }`} />
                ))}
              </div>

              <div className="min-h-[220px]">
                {cards[ci].heading && (
                  <h3 className="text-xl font-bold text-slate-900 mb-4">{cards[ci].heading}</h3>
                )}
                <div className="space-y-2.5">
                  {cards[ci].body.map((line, i) => (
                    <p key={i} className="text-slate-700 leading-relaxed">{line}</p>
                  ))}
                </div>
              </div>
            </div>
          )}

          {phase === "quiz" && quiz.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
                <ClipboardCheck size={16} />
                <span>Вопрос {qi + 1} из {quiz.length}</span>
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-5">{quiz[qi].question}</h3>
              <div className="space-y-2">
                {quiz[qi].options.map((opt, idx) => {
                  const chosen = answers[qi] === idx;
                  return (
                    <button
                      key={idx}
                      onClick={() => pickAnswer(idx)}
                      className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${
                        chosen
                          ? "border-brand-500 bg-brand-50 text-brand-800"
                          : "border-slate-200 hover:bg-slate-50 text-slate-700"
                      }`}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {phase === "result" && result && (
            <div className="text-center py-6">
              {result.step_status === "passed" ? (
                <>
                  <Trophy size={44} className="text-amber-500 mx-auto mb-3" />
                  <h3 className="text-2xl font-bold text-slate-900 mb-1">Шаг пройден!</h3>
                </>
              ) : (
                <>
                  <RotateCcw size={44} className="text-slate-400 mx-auto mb-3" />
                  <h3 className="text-2xl font-bold text-slate-900 mb-1">Почти получилось</h3>
                </>
              )}
              {result.grade && (
                <p className="text-slate-500 mb-5">
                  Правильно {result.grade.correct} из {result.grade.total} ·
                  результат {Math.round(result.grade.score * 100)}%
                </p>
              )}

              {/* Разбор ответов */}
              {result.grade?.details?.length > 0 && (
                <div className="text-left space-y-2 mb-6">
                  {result.grade.details.map((d, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      {d.is_correct
                        ? <CheckCircle2 size={16} className="text-green-600 mt-0.5 flex-shrink-0" />
                        : <XCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />}
                      <span className="text-slate-700">{d.question}</span>
                    </div>
                  ))}
                </div>
              )}

              {result.step_status === "passed" ? (
                <button onClick={onCompleted} className="btn btn-primary w-full">
                  {result.enrollment_status === "completed" ? "Завершить курс" : "Дальше"}
                </button>
              ) : (
                <button onClick={restart} className="btn btn-primary w-full">
                  <RotateCcw size={16} className="mr-2" /> Пройти ещё раз
                </button>
              )}
            </div>
          )}
        </div>

        {/* Низ: навигация (только на этапе карточек/теста) */}
        {phase === "cards" && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-slate-200">
            <button
              onClick={prevCard}
              disabled={ci === 0}
              className="btn btn-secondary disabled:opacity-40"
            >
              <ChevronLeft size={16} className="mr-1" /> Назад
            </button>
            <button onClick={nextCard} disabled={quizLoading} className="btn btn-primary">
              {quizLoading
                ? <><Loader2 size={16} className="mr-2 animate-spin" /> Готовим тест…</>
                : ci < cards.length - 1
                  ? <>Далее <ChevronRight size={16} className="ml-1" /></>
                  : step.require_quiz ? <>К тесту <ChevronRight size={16} className="ml-1" /></>
                    : <>Завершить <CheckCircle2 size={16} className="ml-1" /></>}
            </button>
          </div>
        )}

        {phase === "quiz" && quiz.length > 0 && (
          <div className="flex items-center justify-end px-5 py-3 border-t border-slate-200">
            <button
              onClick={nextQuestion}
              disabled={answers[qi] === -1 || submitting}
              className="btn btn-primary disabled:opacity-40"
            >
              {submitting
                ? <><Loader2 size={16} className="mr-2 animate-spin" /> Проверяем…</>
                : qi < quiz.length - 1 ? <>Следующий <ChevronRight size={16} className="ml-1" /></>
                  : <>Завершить тест <CheckCircle2 size={16} className="ml-1" /></>}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
