"""Тесты «AI-соавтора стандартов» (M8).

Проверяем БЕЗ сети:
  * предложения строятся из РЕАЛЬНЫХ пробелов (вопросов без ответа);
  * антигаллюцинация: выдуманные моделью номера вопросов отбрасываются;
  * запасной режим без модели — каждый пробел отдельной темой;
  * черновик стандарта собирается из ответа модели (скриптованной);
  * пробел можно отметить закрытым.
"""

import json

import pytest

from product.modules import accounts, coauthor
from product.db import models as m


class ScriptedLLM:
    """Провайдер-заглушка: call(...) возвращает заранее заданный текст."""
    def __init__(self, text):
        self.text = text

    def call(self, system, messages, tools):
        return {"text": self.text, "tool_calls": [], "stop_reason": "end_turn",
                "raw_content": [{"type": "text", "text": self.text}]}


def _company(db):
    company, owner = accounts.register_company(
        db, company_name="Net", slug="net",
        owner_email="o@net.io", owner_password="secret1", owner_name="")
    db.commit()
    return company


def _add_gap(db, company_id, question):
    g = m.QAGap(company_id=company_id, question=question, best_score=0.1)
    db.add(g)
    db.commit()
    return g


def test_suggest_groups_real_gaps(db):
    company = _company(db)
    _add_gap(db, company.id, "Как оформить отпуск?")
    _add_gap(db, company.id, "Сколько дней отпуска положено?")
    _add_gap(db, company.id, "Какой график работы в праздники?")
    # Модель группирует и ссылается на номера 1 и 2 (реальные) + 99 (выдуманный).
    llm = ScriptedLLM(json.dumps([
        {"title": "Регламент отпусков", "rationale": "часто спрашивают",
         "question_numbers": [1, 2, 99]},
    ], ensure_ascii=False))
    res = coauthor.suggest_from_gaps(db, company.id, llm=llm)
    assert res["has_gaps"] is True
    assert res["count"] == 3
    s = res["suggestions"][0]
    assert s["title"] == "Регламент отпусков"
    # Выдуманный номер 99 отброшен, остались только реальные вопросы из базы.
    assert len(s["questions"]) == 2
    real = {"Как оформить отпуск?", "Сколько дней отпуска положено?",
            "Какой график работы в праздники?"}
    assert all(q in real for q in s["questions"])


def test_suggest_fallback_without_model(db):
    company = _company(db)
    _add_gap(db, company.id, "Как вернуть абонемент?")
    # Модель «сломалась» → запасной режим: пробел как отдельная тема.
    llm = ScriptedLLM("это не json")
    res = coauthor.suggest_from_gaps(db, company.id, llm=llm)
    assert res["has_gaps"] is True
    assert res["suggestions"]
    assert "абонемент" in res["suggestions"][0]["questions"][0].lower()


def test_suggest_no_gaps(db):
    company = _company(db)
    res = coauthor.suggest_from_gaps(db, company.id)
    assert res["has_gaps"] is False
    assert res["suggestions"] == []


def test_draft_standard(db):
    company = _company(db)
    llm = ScriptedLLM(json.dumps({
        "title": "Регламент возврата абонементов",
        "category": "Администраторам",
        "content": "1. Общие положения.\n1.1. Возврат оформляется по заявлению.",
    }, ensure_ascii=False))
    d = coauthor.draft_standard(db, company.id,
                                instruction="Опиши порядок возврата абонементов", llm=llm)
    assert d["title"] == "Регламент возврата абонементов"
    assert "Возврат" in d["content"]


def test_draft_requires_instruction(db):
    company = _company(db)
    with pytest.raises(coauthor.CoAuthorError):
        coauthor.draft_standard(db, company.id, instruction="  ", llm=ScriptedLLM("{}"))


def test_resolve_gap(db):
    company = _company(db)
    g = _add_gap(db, company.id, "Вопрос")
    assert coauthor.resolve_gap(db, company.id, g.id) is True
    db.refresh(g)
    assert g.resolved is True
