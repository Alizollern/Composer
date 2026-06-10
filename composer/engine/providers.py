"""
Шов 1 — провайдеры LLM.

Весь код зависит только от интерфейса LLMProvider, а не от конкретного SDK.
Сегодня Claude; завтра Gemini/GPT добавляются здесь, не трогая агентов.
"""

from abc import ABC, abstractmethod

from composer.config import MODEL, MAX_TOKENS


class LLMProvider(ABC):
    @abstractmethod
    def call(self, system, messages, tools):
        """Вернуть ответ в едином формате (см. ClaudeProvider.call)."""
        ...


class ClaudeProvider(LLMProvider):
    def __init__(self, model=None, max_tokens=None):
        from anthropic import Anthropic
        self.client = Anthropic()  # ключ из ANTHROPIC_API_KEY
        self.model = model or MODEL
        self.max_tokens = max_tokens or MAX_TOKENS

    def call(self, system, messages, tools):
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            tools=[t["schema"] for t in tools],
        )
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
