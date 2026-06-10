"""
Интеграция: универсальный HTTP-запрос.

Это «отмычка» к любому REST API: агент может дёрнуть внешний сервис.
Через неё позже легко строятся конкретные коннекторы (Slack, Notion, CRM…).
"""

import json
import urllib.request
import urllib.error

from composer.tools.base import integration

_MAX = 8000  # ограничиваем тело ответа, чтобы не раздувать контекст


@integration(
    name="http_request",
    description=("Выполнить HTTP-запрос к внешнему API. "
                 "method: GET/POST/PUT/PATCH/DELETE. "
                 "Возвращает статус и тело ответа (обрезается)."),
    input_schema={
        "type": "object",
        "properties": {
            "method": {"type": "string", "description": "GET, POST, PUT, PATCH, DELETE"},
            "url": {"type": "string"},
            "headers": {"type": "object", "description": "Заголовки (опц.)"},
            "json_body": {"type": "object", "description": "Тело запроса как JSON (опц.)"},
        },
        "required": ["method", "url"],
    },
    category="network",
)
def http_request(inp):
    method = (inp.get("method") or "GET").upper()
    url = inp["url"]
    headers = dict(inp.get("headers") or {})
    data = None
    if inp.get("json_body") is not None:
        data = json.dumps(inp["json_body"]).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", "ignore")
            return f"HTTP {resp.status}\n{body[:_MAX]}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore") if e.fp else ""
        return f"HTTP {e.code} {e.reason}\n{body[:_MAX]}"
    except Exception as e:
        return f"Ошибка запроса: {e}"
