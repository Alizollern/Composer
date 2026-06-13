"""Тесты строгого структурированного вывода (ядро: composer.engine.structured).

Проверяем, что:
  * JSON достаётся из «грязного» ответа (markdown-обёртка, префиксы/суффиксы);
  * при битом JSON движок ПЕРЕСПРАШИВАЕТ модель и чинит результат;
  * проверка типа верхнего уровня (object/array) работает;
  * после исчерпания попыток — честный ValueError.

LLM здесь — простая функция-заглушка, без сети.
"""

import json

import pytest

from composer.engine.structured import complete_json, extract_json, parse_json


def test_extract_strips_markdown_fence():
    raw = "```json\n{\"a\": 1}\n```"
    assert json.loads(extract_json(raw)) == {"a": 1}


def test_extract_handles_prefix_and_suffix():
    raw = "Вот ваш ответ: {\"ok\": true}. Готово!"
    assert json.loads(extract_json(raw)) == {"ok": True}


def test_parse_json_type_check():
    with pytest.raises(ValueError):
        parse_json("{\"a\": 1}", expect="array")
    assert parse_json("[1, 2]", expect="array") == [1, 2]


def test_complete_json_happy_path():
    calls = []

    def fn(system, user):
        calls.append(user)
        return "```json\n{\"sentiment\": \"positive\"}\n```"

    data, text = complete_json(fn, "sys", "разбери отзыв", expect="object")
    assert data == {"sentiment": "positive"}
    assert len(calls) == 1  # с первого раза — без переспроса


def test_complete_json_repairs_on_bad_output():
    """Первый ответ битый → движок переспрашивает и получает валидный JSON."""
    seq = ["это не json вообще", "{\"fixed\": true}"]

    def fn(system, user):
        return seq.pop(0)

    data, _ = complete_json(fn, "sys", "верни json", expect="object", retries=1)
    assert data == {"fixed": True}


def test_complete_json_passes_error_to_model_on_retry():
    seen = []

    def fn(system, user):
        seen.append(user)
        return "мусор" if len(seen) == 1 else "[1,2,3]"

    data, _ = complete_json(fn, "sys", "дай массив", expect="array", retries=1)
    assert data == [1, 2, 3]
    # На втором заходе в запрос добавлено указание вернуть строгий JSON.
    assert "JSON" in seen[1] and seen[1] != seen[0]


def test_complete_json_gives_up_after_retries():
    def fn(system, user):
        return "никогда не json"

    with pytest.raises(ValueError):
        complete_json(fn, "sys", "u", expect="object", retries=2)
