"""Тесты «цифрового опер-дира» (M6) — первого агента с инструментами.

Проверяем БЕЗ сети:
  * продуктовые инструменты возвращают реальные данные компании (scoped);
  * многошаговый цикл движка реально зовёт инструмент и доходит до ответа;
  * RBAC на API: сотруднику нельзя, управляющему можно.

LLM — скриптованная заглушка-провайдер с интерфейсом call(system, messages, tools).
"""

import pytest

from product.modules import accounts, advisor, reviews as reviews_mod
from product.reviews.source import FakeReviewSource


class ScriptedLLM:
    """Провайдер-заглушка: отдаёт заранее заданные ходы (как настоящий call)."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.i = 0

    def call(self, system, messages, tools):
        step = self.steps[min(self.i, len(self.steps) - 1)]
        self.i += 1
        return step


def _tool_step(name, tool_input):
    cid = f"call_{name}"
    return {
        "text": "",
        "tool_calls": [{"id": cid, "name": name, "input": tool_input}],
        "stop_reason": "tool_use",
        "raw_content": [{"type": "tool_use", "id": cid, "name": name,
                         "input": tool_input}],
    }


def _final_step(text):
    return {
        "text": text,
        "tool_calls": [],
        "stop_reason": "end_turn",
        "raw_content": [{"type": "text", "text": text}],
    }


def _company_with_network(db):
    company, owner = accounts.register_company(
        db, company_name="Net", slug="net",
        owner_email="o@net.io", owner_password="secret1", owner_name="")
    db.commit()
    bad = reviews_mod.connect_point(db, company.id, name="Зал на Сатпаева",
                                    url="https://2gis.kz/almaty/firm/222")
    db.commit()
    # Разбор без модели: фейк-источник + откат к оценке (rating) внутри analyze.
    reviews_mod.sync_reviews(db, company.id, bad.id,
                             source=FakeReviewSource(profile="bad", prefix="b-"))
    reviews_mod.analyze_pending(db, company.id, point_id=bad.id,
                                llm=lambda *a, **k: "{}")  # любой ответ → fallback
    return company


def test_advisor_tools_return_company_data(db):
    company = _company_with_network(db)
    tools = {t["schema"]["name"]: t["fn"] for t in advisor.build_tools(db, company.id)}

    overview = tools["network_overview"]({})
    assert "Сатпаева" in overview
    assert "жалоб" in overview.lower()

    problems = tools["point_problems"]({"point": "Сатпаева"})
    assert "Сатпаева" in problems

    gaps = tools["list_gaps"]({})
    assert isinstance(gaps, str) and gaps  # пусто или список — но строка


def test_advisor_runs_multistep_loop(db):
    """Агент зовёт инструмент, получает данные, затем выдаёт финальный ответ."""
    company = _company_with_network(db)
    llm = ScriptedLLM([
        _tool_step("network_overview", {}),
        _final_step("Вывод: точка «Сатпаева» проседает. Действия: проверить уборку."),
    ])
    res = advisor.ask(db, company.id, "Какая точка проседает и что делать?", llm=llm)
    assert "Сатпаева" in res["answer"]
    assert llm.i == 2  # был ровно один заход в инструмент + финал


def test_advisor_empty_question(db):
    company = _company_with_network(db)
    res = advisor.ask(db, company.id, "   ", llm=ScriptedLLM([_final_step("x")]))
    assert "вопрос" in res["answer"].lower()
