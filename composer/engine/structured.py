"""
Шов — строгий структурированный вывод (JSON по контракту).

Многим фичам нужен не «свободный» ответ агента, а ПРЕДСКАЗУЕМЫЙ объект по
схеме: разбор отзыва, генерация теста, классификация. Модель иногда оборачивает
JSON в ```-блок, добавляет пояснение или ломает формат. Этот модуль:

  1) аккуратно достаёт JSON из ответа (extract_json / parse_json) —
     терпимо к markdown-обёрткам и префиксам/суффиксам;
  2) complete_json(...) — делает вызов и, если JSON битый, ПЕРЕСПРАШИВАЕТ
     модель с описанием ошибки (до `retries` раз). Это поднимает надёжность
     всех фич сразу, без агентного цикла и без инструментов.

Движок не привязан к провайдеру: complete_json принимает callable
`complete_fn(system, user) -> str`. Продукт передаёт сюда свой контролируемый
вызов LLM (product/brain.complete), поэтому логирование и подмена в тестах
работают без изменений.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Tuple

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def extract_json(text: str) -> str:
    """Вернуть JSON-фрагмент из ответа модели (снять ```-обёртку/префиксы)."""
    s = (text or "").strip()
    m = _FENCE_RE.match(s)
    if m:
        s = m.group(1).strip()
    if s.startswith("{") or s.startswith("["):
        return s
    # Иначе берём от первой открывающей скобки до последней закрывающей того же
    # типа (терпим к «Вот ваш JSON: {...}. Готово.»).
    candidates = [i for i in (s.find("{"), s.find("[")) if i != -1]
    if not candidates:
        return s
    i = min(candidates)
    close = "}" if s[i] == "{" else "]"
    j = s.rfind(close)
    return s[i:j + 1] if j > i else s[i:]


def parse_json(text: str, expect: str = "any") -> Any:
    """Разобрать JSON и (опц.) проверить тип верхнего уровня.

    expect: "object" | "array" | "any".
    Бросает ValueError/json.JSONDecodeError при несоответствии.
    """
    data = json.loads(extract_json(text))
    if expect == "object" and not isinstance(data, dict):
        raise ValueError("ожидался JSON-объект")
    if expect == "array" and not isinstance(data, list):
        raise ValueError("ожидался JSON-массив")
    return data


_SHAPE = {"object": "JSON-объект", "array": "JSON-массив", "any": "валидный JSON"}

_REPAIR = (
    "\n\n[ВАЖНО] Прошлый ответ не распарсился как JSON ({err}). "
    "Верни СТРОГО {shape} — без markdown, без ```-обёрток, без пояснений "
    "до или после. Только сам JSON."
)


def complete_json(
    complete_fn: Callable[[str, str], str],
    system: str,
    user: str,
    *,
    expect: str = "any",
    retries: int = 1,
) -> Tuple[Any, str]:
    """Вызвать модель и вернуть (разобранный JSON, сырой текст последнего ответа).

    complete_fn(system, user) -> str — контролируемый одиночный вызов LLM.
    При битом JSON переспрашиваем (повторяем вызов) до `retries` раз, добавляя
    к запросу описание ошибки. Бросает ValueError, если так и не получили
    валидный JSON.
    """
    shape = _SHAPE.get(expect, _SHAPE["any"])
    cur_user = user
    last_err: Exception | None = None
    text = ""
    for attempt in range(retries + 1):
        text = (complete_fn(system, cur_user) or "").strip()
        try:
            return parse_json(text, expect), text
        except Exception as e:  # json.JSONDecodeError или ValueError по типу
            last_err = e
            cur_user = user + _REPAIR.format(err=e, shape=shape)
    raise ValueError(
        f"Модель не вернула валидный JSON после {retries + 1} попыток: {last_err}")
