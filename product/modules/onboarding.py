"""
M3 — Онбординг и обучение (генерация теста по стандарту).

Идея (ТЗ): сотрудник изучает стандарт, а система проверяет усвоение —
автоматически готовит тест ПО КОНКРЕТНОМУ документу и оценивает ответы.

Строгое заземление: вопросы и варианты строятся ТОЛЬКО по тексту стандарта
(как и ответы чат-бота в M2) — модель не должна спрашивать про то, чего в
документе нет. Каждый вопрос несёт source_quote — цитату из стандарта, на
которой он основан (проверяемость и доверие).

Тест генерируется по запросу и не требует отдельных таблиц: это функция над
текстом версии. Хранение попыток/прогресса — следующий шаг (отдельный шов).
"""

from __future__ import annotations

import json
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from product import brain
from product.db import models as m
from product.modules.knowledge import get_document

_SYSTEM = (
    "Ты готовишь проверочный тест для сотрудника по внутреннему стандарту компании. "
    "Составляй вопросы СТРОГО и ТОЛЬКО по приведённому тексту стандарта — ничего не "
    "придумывай и не используй общие знания.\n"
    "Верни РОВНО валидный JSON-массив без пояснений и без markdown. Каждый элемент:\n"
    '{"question": "...", "options": ["A","B","C","D"], '
    '"correct_index": 0, "source_quote": "точная цитата из текста"}\n'
    "Ровно 4 варианта; верный ровно один; correct_index — индекс верного (0..3); "
    "source_quote — дословный фрагмент из стандарта, подтверждающий ответ."
)


class QuizError(Exception):
    """Не удалось сгенерировать корректный тест (модель вернула мусор)."""


def _parse_quiz(raw: str) -> List[dict]:
    """Достать JSON-массив вопросов из ответа модели (терпим к ```-обёрткам)."""
    text = raw.strip()
    # Снимаем markdown-ограждение ```json ... ```
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # На случай префиксов — берём от первой '[' до последней ']'.
    if not text.startswith("["):
        i, j = text.find("["), text.rfind("]")
        if i != -1 and j != -1 and j > i:
            text = text[i:j + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise QuizError(f"Модель вернула невалидный JSON: {e}")
    if not isinstance(data, list):
        raise QuizError("Ожидался JSON-массив вопросов")
    return data


def _validate(items: List[dict]) -> List[dict]:
    """Отфильтровать структурно корректные вопросы; нормализовать."""
    clean: List[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        q = str(it.get("question", "")).strip()
        opts = it.get("options")
        ci = it.get("correct_index")
        if not q or not isinstance(opts, list) or len(opts) != 4:
            continue
        if not isinstance(ci, int) or not (0 <= ci < 4):
            continue
        clean.append({
            "question": q,
            "options": [str(o) for o in opts],
            "correct_index": ci,
            "source_quote": str(it.get("source_quote", "")).strip(),
        })
    if not clean:
        raise QuizError("Не получилось собрать ни одного корректного вопроса")
    return clean


def generate_quiz(text: str, *, num_questions: int = 5, llm=None,
                  company: str | None = None) -> List[dict]:
    """Сгенерировать тест по тексту стандарта. Возвращает список вопросов."""
    if not text.strip():
        raise QuizError("Пустой текст стандарта")
    user = (
        f"Сделай {num_questions} вопросов с одним верным ответом по тексту ниже.\n\n"
        f"=== ТЕКСТ СТАНДАРТА ===\n{text}"
    )
    raw = brain.complete(_SYSTEM, user, llm=llm,
                         operation="quiz_generate", company=company)
    return _validate(_parse_quiz(raw))[:num_questions]


def generate_quiz_for_document(
    db: Session, company_id: str, document_id: str, *,
    num_questions: int = 5, llm=None,
) -> List[dict]:
    """Сгенерировать тест по текущей версии документа компании."""
    doc = get_document(db, company_id, document_id)
    version = db.get(m.DocumentVersion, doc.current_version_id) if doc.current_version_id else None
    if version is None:
        raise QuizError("У документа нет текущей версии")
    return generate_quiz(version.content, num_questions=num_questions, llm=llm,
                         company=company_id)


def public_questions(questions: List[dict]) -> List[dict]:
    """Вид теста для клиента: только вопрос и варианты, без верного ответа и
    цитаты. Правильные ответы (correct_index/source_quote) остаются на сервере."""
    return [{"question": q["question"], "options": list(q["options"])}
            for q in questions]


def store_quiz(db: Session, company_id: str, document_id: str,
               questions: List[dict], *, user_id: Optional[str] = None) -> m.QuizInstance:
    """Сохранить сгенерированный тест (с ответами) на сервере. Возвращает запись,
    её id выступает токеном теста для клиента."""
    inst = m.QuizInstance(
        company_id=company_id, document_id=document_id,
        user_id=user_id, questions=questions)
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def load_quiz(db: Session, company_id: str, quiz_token: str) -> m.QuizInstance:
    """Достать сохранённый тест по токену в рамках компании (иначе KeyError)."""
    inst = db.get(m.QuizInstance, quiz_token)
    if inst is None or inst.company_id != company_id:
        raise KeyError("Тест не найден")
    return inst


def grade(quiz: List[dict], answers: List[int]) -> dict:
    """Оценить ответы (список индексов) против теста. Вернуть счёт и разбор."""
    total = len(quiz)
    details = []
    correct = 0
    for i, q in enumerate(quiz):
        given = answers[i] if i < len(answers) else None
        ok = (given == q["correct_index"])
        correct += int(ok)
        details.append({
            "question": q["question"],
            "given_index": given,
            "correct_index": q["correct_index"],
            "is_correct": ok,
            "source_quote": q.get("source_quote", ""),
        })
    return {
        "total": total,
        "correct": correct,
        "score": round(correct / total, 3) if total else 0.0,
        "passed": (correct / total) >= 0.8 if total else False,
        "details": details,
    }
