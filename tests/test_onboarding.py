"""Тесты M3 (онбординг): генерация теста по стандарту, парсинг, оценивание."""

import pytest

from product.modules import onboarding
from product.modules.onboarding import QuizError, grade, generate_quiz

VALID_JSON = (
    '[{"question": "Температура эспрессо?", '
    '"options": ["80", "92", "100", "60"], "correct_index": 1, '
    '"source_quote": "Эспрессо при 92 градуса."}, '
    '{"question": "До скольки взбивать молоко?", '
    '"options": ["50", "65", "80", "90"], "correct_index": 1, '
    '"source_quote": "Молоко до 65."}]'
)


class FakeProvider:
    def __init__(self, text):
        self.text = text

    def call(self, system, messages, tools):
        return {"text": self.text, "tool_calls": [], "stop_reason": "end_turn",
                "raw_content": []}


def test_generate_quiz_parses_json():
    quiz = generate_quiz("Эспрессо при 92. Молоко до 65.",
                         num_questions=2, llm=FakeProvider(VALID_JSON))
    assert len(quiz) == 2
    assert quiz[0]["options"] == ["80", "92", "100", "60"]
    assert quiz[0]["correct_index"] == 1


def test_generate_quiz_strips_markdown_fence():
    fenced = "```json\n" + VALID_JSON + "\n```"
    quiz = generate_quiz("текст", llm=FakeProvider(fenced))
    assert len(quiz) == 2


def test_generate_quiz_rejects_garbage():
    with pytest.raises(QuizError):
        generate_quiz("текст", llm=FakeProvider("это не json вовсе"))


def test_generate_quiz_filters_malformed_items():
    mixed = (
        '[{"question": "ok", "options": ["a","b","c","d"], "correct_index": 0}, '
        '{"question": "bad", "options": ["a","b"], "correct_index": 0}]'
    )
    quiz = generate_quiz("текст", llm=FakeProvider(mixed))
    assert len(quiz) == 1  # битый вопрос с 2 вариантами отброшен


def test_grade_scores_and_passes():
    quiz = generate_quiz("текст", num_questions=2, llm=FakeProvider(VALID_JSON))
    res = grade(quiz, [1, 1])
    assert res["correct"] == 2 and res["total"] == 2
    assert res["score"] == 1.0 and res["passed"] is True


def test_grade_partial_and_missing_answers():
    quiz = generate_quiz("текст", num_questions=2, llm=FakeProvider(VALID_JSON))
    res = grade(quiz, [1])  # ответ только на первый
    assert res["correct"] == 1
    assert res["details"][1]["given_index"] is None
    assert res["passed"] is False
