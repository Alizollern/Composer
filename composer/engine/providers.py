"""
Шов 1 — провайдеры LLM.

Весь код зависит только от интерфейса LLMProvider, а не от конкретного SDK.
Сегодня Claude; завтра Gemini/GPT добавляются здесь, не трогая агентов.

ClaudeProvider устойчив к rate-limit (429) и перегрузке (529): ждёт по заголовку
retry-after или экспоненциальной паузой и повторяет запрос — один временный 429
не должен ронять весь прогон.
"""

import time
import uuid
from abc import ABC, abstractmethod

from composer.config import (MODEL, MAX_TOKENS, MAX_RETRIES,
                             PROVIDER, GEMINI_MODEL)


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


_CACHE = {"type": "ephemeral"}


def _with_cache(system, tools, messages):
    """Расставляет точки prompt-кэша (cache_control) так, чтобы повторно
    пересылаемый префикс тарифицировался со скидкой ~90%:
      1) системный промпт,
      2) блок схем инструментов (статичен на весь прогон),
      3) последнее сообщение — чтобы кэшировался ВЕСЬ контекст до него
         (история диалога растёт, но префикс переиспользуется).
    Всего ≤3 точки (лимит API — 4). Структуры не мутируем — копии на вызов."""
    # 1) system -> блочная форма с кэшем
    system_param = ([{"type": "text", "text": system, "cache_control": _CACHE}]
                    if system else system)

    # 2) кэш на последней схеме инструмента (кэшируется весь блок tools)
    tools_param = [t["schema"] for t in tools]
    if tools_param:
        tools_param = tools_param[:-1] + [{**tools_param[-1], "cache_control": _CACHE}]

    # 3) кэш на последнем блоке последнего сообщения
    messages_param = messages
    if messages:
        last = messages[-1]
        content = last.get("content")
        if isinstance(content, str):
            new_content = [{"type": "text", "text": content, "cache_control": _CACHE}]
        elif isinstance(content, list) and content and isinstance(content[-1], dict):
            new_content = content[:-1] + [{**content[-1], "cache_control": _CACHE}]
        else:
            new_content = content
        messages_param = messages[:-1] + [{**last, "content": new_content}]

    return system_param, tools_param, messages_param


class ClaudeProvider(LLMProvider):
    def __init__(self, model=None, max_tokens=None, max_retries=None):
        from anthropic import Anthropic
        self.client = Anthropic()  # ключ из ANTHROPIC_API_KEY
        self.model = model or MODEL
        self.max_tokens = max_tokens or MAX_TOKENS
        self.max_retries = max_retries or MAX_RETRIES

    def _create(self, system, messages, tools):
        from anthropic import RateLimitError, APIStatusError, APIConnectionError

        system_param, tools_param, messages_param = _with_cache(system, tools, messages)

        last = None
        for attempt in range(self.max_retries):
            try:
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_param,
                    messages=messages_param,
                    tools=tools_param,
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


# =====================================================================
# Gemini (бесплатный тариф Google AI Studio) — второй провайдер.
#
# Тот же интерфейс call(system, messages, tools), но формат у Gemini свой:
# вместо «блоков контента» Anthropic — contents с parts (text/function_call/
# function_response). Этот адаптер переводит наш канонический формат истории
# (Anthropic-подобные блоки, которые складывает loop.py) в формат Gemini и
# обратно, СОХРАНЯЯ id вызовов инструментов — чтобы сопоставление tool_result
# в loop.py продолжало работать без изменений в движке.
#
# raw_content, который возвращает этот провайдер, — это список простых dict-
# блоков в Anthropic-стиле ({"type":"text"|"tool_use", ...}). Так история
# остаётся в одном каноническом виде независимо от провайдера.
# =====================================================================
class GeminiProvider(LLMProvider):
    def __init__(self, model=None, max_tokens=None, max_retries=None):
        from google import genai
        # ключ из GEMINI_API_KEY или GOOGLE_API_KEY (SDK читает сам),
        # но передаём явно для предсказуемости.
        import os
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=key) if key else genai.Client()
        # Если сверху прокинули claude-модель (model из манифеста агента),
        # игнорируем её и берём gemini-модель из конфига.
        self.model = model if (model and str(model).startswith("gemini")) else GEMINI_MODEL
        self.max_tokens = max_tokens or MAX_TOKENS
        self.max_retries = max_retries or MAX_RETRIES

    # ---- перевод НАШ формат -> Gemini ----
    @staticmethod
    def _tools_to_gemini(tools):
        from google.genai import types
        decls = []
        for t in tools:
            s = t["schema"]
            decls.append(types.FunctionDeclaration(
                name=s["name"],
                description=s.get("description", ""),
                # input_schema — стандартный JSON Schema, кладём как есть.
                parameters_json_schema=s.get("input_schema") or {"type": "object",
                                                                  "properties": {}},
            ))
        return [types.Tool(function_declarations=decls)] if decls else None

    @staticmethod
    def _id_to_name(messages):
        """Сканируем ассистентские ходы, собираем id вызова -> имя инструмента,
        чтобы при переводе tool_result знать имя функции (Gemini требует name)."""
        mapping = {}
        for m in messages:
            content = m.get("content")
            if m.get("role") == "assistant" and isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        mapping[b.get("id")] = b.get("name")
        return mapping

    def _messages_to_gemini(self, messages):
        from google.genai import types
        id2name = self._id_to_name(messages)
        contents = []
        for m in messages:
            role = m.get("role")
            content = m.get("content")
            if role == "user" and isinstance(content, str):
                contents.append(types.Content(
                    role="user", parts=[types.Part(text=content)]))
            elif role == "user" and isinstance(content, list):
                parts = []
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        name = id2name.get(b.get("tool_use_id"), "tool")
                        parts.append(types.Part(
                            function_response=types.FunctionResponse(
                                id=b.get("tool_use_id"),
                                name=name,
                                response={"result": str(b.get("content", ""))})))
                    elif isinstance(b, dict) and b.get("type") == "text":
                        parts.append(types.Part(text=b.get("text", "")))
                if parts:
                    contents.append(types.Content(role="user", parts=parts))
            elif role == "assistant" and isinstance(content, list):
                parts = []
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text"):
                        parts.append(types.Part(text=b["text"]))
                    elif b.get("type") == "tool_use":
                        part = types.Part(
                            function_call=types.FunctionCall(
                                id=b.get("id"), name=b.get("name"),
                                args=b.get("input") or {}))
                        # возвращаем метку рассуждения, если она была — этого
                        # требует Gemini для многошаговых вызовов инструментов
                        sig = b.get("thought_signature")
                        if sig is not None:
                            part.thought_signature = sig
                        parts.append(part)
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
            elif role == "assistant" and isinstance(content, str):
                contents.append(types.Content(
                    role="model", parts=[types.Part(text=content)]))
        return contents

    def _create(self, system, messages, tools):
        from google.genai import types
        from google.genai import errors

        config = types.GenerateContentConfig(
            system_instruction=system or None,
            tools=self._tools_to_gemini(tools),
            max_output_tokens=self.max_tokens,
            # выключаем авто-вызов: нам нужны function_call наружу, не исполнение
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True),
        )
        contents = self._messages_to_gemini(messages)

        last = None
        for attempt in range(self.max_retries):
            try:
                return self.client.models.generate_content(
                    model=self.model, contents=contents, config=config)
            except errors.APIError as e:
                code = getattr(e, "code", None) or getattr(e, "status_code", None)
                if code not in (429, 500, 502, 503, 529):
                    raise
                last = e
                wait = min(2 ** attempt * 5, 60)
            if attempt < self.max_retries - 1:
                time.sleep(wait)
        raise last

    def call(self, system, messages, tools):
        resp = self._create(system, messages, tools)
        text_parts, tool_calls, raw_content = [], [], []

        candidates = getattr(resp, "candidates", None) or []
        parts = []
        if candidates and getattr(candidates[0], "content", None):
            parts = candidates[0].content.parts or []

        for part in parts:
            txt = getattr(part, "text", None)
            fc = getattr(part, "function_call", None)
            if txt:
                text_parts.append(txt)
                raw_content.append({"type": "text", "text": txt})
            elif fc:
                cid = getattr(fc, "id", None) or f"gemini_{uuid.uuid4().hex[:12]}"
                args = dict(fc.args) if fc.args else {}
                tool_calls.append({"id": cid, "name": fc.name, "input": args})
                block = {"type": "tool_use", "id": cid,
                         "name": fc.name, "input": args}
                # Gemini 2.5 (thinking) возвращает непрозрачную метку рассуждения
                # на каждом вызове инструмента; её ОБЯЗАТЕЛЬНО вернуть в истории
                # на следующих шагах, иначе 400 INVALID_ARGUMENT.
                sig = getattr(part, "thought_signature", None)
                if sig is not None:
                    block["thought_signature"] = sig
                raw_content.append(block)

        return {
            "text": "\n".join(text_parts),
            "tool_calls": tool_calls,
            "stop_reason": "tool_use" if tool_calls else "end_turn",
            "raw_content": raw_content,
        }


def get_provider(name=None, **kwargs):
    """Фабрика провайдеров — точка расширения для мультимодельности.
    Имя по умолчанию берётся из COMPOSER_PROVIDER (claude|gemini)."""
    name = name or PROVIDER
    if name == "claude":
        return ClaudeProvider(**kwargs)
    if name == "gemini":
        return GeminiProvider(**kwargs)
    raise ValueError(f"Неизвестный провайдер: {name}")
