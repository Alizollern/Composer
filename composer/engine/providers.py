"""
Шов 1 — провайдеры LLM.

Весь код зависит только от интерфейса LLMProvider, а не от конкретного SDK.
Сегодня Claude; завтра Gemini/GPT добавляются здесь, не трогая агентов.

ClaudeProvider устойчив к rate-limit (429) и перегрузке (529): ждёт по заголовку
retry-after или экспоненциальной паузой и повторяет запрос — один временный 429
не должен ронять весь прогон.
"""

import time
from abc import ABC, abstractmethod

from composer.config import MODEL, MAX_TOKENS, MAX_RETRIES


class LLMProvider(ABC):
    @abstractmethod
    def call(self, system, messages, tools):
        """Вернуть ответ в едином формате (см. ClaudeProvider.call)."""
        ...


def _retry_after(err):
    """Сколько секунд ждать по заголовку ответа (если есть)."""
    try:
        ra = err.response.headers.get("retry-after")
        return float(ra) if ra else None
    except Exception:
        return None


class ClaudeProvider(LLMProvider):
    def __init__(self, model=None, max_tokens=None, max_retries=None):
        from anthropic import Anthropic
        self.client = Anthropic()  # ключ из ANTHROPIC_API_KEY
        self.model = model or MODEL
        self.max_tokens = max_tokens or MAX_TOKENS
        self.max_retries = max_retries or MAX_RETRIES

    def _create(self, system, messages, tools):
        from anthropic import RateLimitError, APIStatusError, APIConnectionError

        last = None
        for attempt in range(self.max_retries):
            try:
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system,
                    messages=messages,
                    tools=[t["schema"] for t in tools],
                )
            except RateLimitError as e:          # 429 — лимит токенов/мин
                last = e
                wait = _retry_after(e) or min(2 ** attempt * 5, 60)
            except APIConnectionError as e:      # сетевые сбои
                last = e
                wait = min(2 ** attempt, 20)
            except APIStatusError as e:          # 529 перегрузка / 5xx
                if e.status_code not in (500, 502, 503, 529):
                    raise
                last = e
                wait = min(2 ** attempt * 2, 40)
            if attempt < self.max_retries - 1:
                time.sleep(wait)
        raise last

    def call(self, system, messages, tools):
        resp = self._create(system, messages, tools)
        text_parts, tool_calls = [], []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input})
        return {
            "text": "\n".join(text_parts),
            "tool_calls": tool_calls,
            "stop_reason": resp.stop_reason,
            "raw_content": resp.content,
        }


def get_provider(name="claude", **kwargs):
    """Фабрика провайдеров — точка расширения для мультимодельности."""
    if name == "claude":
        return ClaudeProvider(**kwargs)
    raise ValueError(f"Неизвестный провайдер: {name}")
