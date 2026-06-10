"""
Шов 2 — цикл агента (worker).

Один агент = одна функция run_agent. Оркестратор/чат вызывают её.
Движок ничего не печатает сам — он эмитит СОБЫТИЯ через on_event(callback).
CLI рендерит их в терминал, API стримит во фронтенд. Это и есть "адаптивность".

Формат событий (dict):
  {"type": "text",        "text": str}
  {"type": "tool_call",   "name": str, "input": dict}
  {"type": "tool_result", "name": str, "output": str}
"""

from composer.config import MAX_STEPS

DEFAULT_SYSTEM = (
    "Ты — агент Composer AI. Используй доступные инструменты, выполняй "
    "задачу шаг за шагом. Когда задача выполнена — кратко отчитайся."
)


def _emit(on_event, **event):
    if on_event:
        on_event(event)


def run_agent(prompt, llm, tools, memory,
              system=DEFAULT_SYSTEM, max_steps=None, history=None, on_event=None):
    max_steps = max_steps or MAX_STEPS
    tool_map = {t["schema"]["name"]: t["fn"] for t in tools if "fn" in t}
    messages = history if history is not None else []
    messages.append({"role": "user", "content": prompt})

    for _ in range(max_steps):
        result = llm.call(system, messages, tools)

        if result["text"]:
            _emit(on_event, type="text", text=result["text"])

        # Модель не зовёт инструменты — закончила.
        if result["stop_reason"] != "tool_use":
            messages.append({"role": "assistant", "content": result["raw_content"]})
            memory.write("last_answer", result["text"])
            return result["text"]

        messages.append({"role": "assistant", "content": result["raw_content"]})
        tool_results = []
        for call in result["tool_calls"]:
            _emit(on_event, type="tool_call", name=call["name"], input=call["input"])
            try:
                output = tool_map[call["name"]](call["input"])
            except Exception as e:
                output = f"Ошибка инструмента: {e}"
            _emit(on_event, type="tool_result", name=call["name"], output=str(output)[:500])
            tool_results.append({
                "type": "tool_result", "tool_use_id": call["id"], "content": str(output),
            })
        messages.append({"role": "user", "content": tool_results})

    return "Достигнут лимит шагов."
