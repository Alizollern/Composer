"""
Шов 2 — цикл агента (worker).

Один агент = одна функция run_agent. Оркестратор/чат/делегирование вызывают её.
Движок ничего не печатает сам — он эмитит СОБЫТИЯ через on_event(callback).
CLI рендерит их в терминал, API стримит во фронтенд. Это и есть "адаптивность".

Параллелизм: если модель за один ход просит несколько инструментов
(в т.ч. несколько суб-агентов) и parallel_tools=True — они выполняются
ОДНОВРЕМЕННО в пуле потоков. Так оркестратор запускает агентов параллельно.

Формат событий (dict):
  {"type": "text",         "text": str}
  {"type": "tool_call",    "name": str, "input": dict}
  {"type": "tool_result",  "name": str, "output": str}
  {"type": "subagent_start","agent": str, "task": str, "depth": int}
  {"type": "subagent_done", "agent": str, "depth": int, "size": int}
"""

from concurrent.futures import ThreadPoolExecutor

from composer.config import MAX_STEPS, MAX_PARALLEL

DEFAULT_SYSTEM = (
    "Ты — агент Composer AI. Используй доступные инструменты, выполняй "
    "задачу шаг за шагом. Когда задача выполнена — кратко отчитайся."
)


def _emit(on_event, **event):
    if on_event:
        on_event(event)


def run_agent(prompt, llm, tools, memory,
              system=DEFAULT_SYSTEM, max_steps=None, history=None,
              on_event=None, parallel_tools=False):
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

        def run_one(call):
            _emit(on_event, type="tool_call", name=call["name"], input=call["input"])
            try:
                output = tool_map[call["name"]](call["input"])
            except KeyError:
                output = f"Неизвестный инструмент: {call['name']}"
            except Exception as e:  # инструмент не должен ронять весь цикл
                output = f"Ошибка инструмента: {e}"
            output = str(output)
            _emit(on_event, type="tool_result", name=call["name"], output=output[:500])
            return {"type": "tool_result", "tool_use_id": call["id"], "content": output}

        calls = result["tool_calls"]
        if parallel_tools and len(calls) > 1:
            # ThreadPoolExecutor.map сохраняет порядок — tool_use_id не перепутаются.
            with ThreadPoolExecutor(max_workers=min(len(calls), MAX_PARALLEL)) as ex:
                tool_results = list(ex.map(run_one, calls))
        else:
            tool_results = [run_one(c) for c in calls]

        messages.append({"role": "user", "content": tool_results})

    return "Достигнут лимит шагов."
