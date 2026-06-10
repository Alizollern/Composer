"""
Раннер одного агента по имени.

Универсальная точка запуска: грузит агента из папки, при наличии subagents
подключает инструменты делегирования (тогда агент работает как оркестратор),
прогоняет run_agent и детерминированно сохраняет результат в его output-файл.

Используется и для одиночного запуска агента, и как основа динамической
оркестрации (planner.orchestrate_dynamic).
"""

from composer.config import WORKSPACE
from composer.engine.providers import ClaudeProvider
from composer.engine.memory import InMemoryMemory
from composer.engine.loop import run_agent
from composer.agents.loader import load_agent
from composer.orchestration.agent_tools import make_agent_tools


def run_agent_by_name(name, task, llm=None, on_event=None,
                      memory=None, history=None):
    agent = load_agent(name)
    llm = llm or ClaudeProvider(model=agent.get("model"))

    tools = list(agent["tools"])
    subs = agent.get("subagents") or []
    if subs:
        tools += make_agent_tools(subs, llm, on_event)

    final = run_agent(
        task, llm, tools, memory or InMemoryMemory(),
        system=agent["system"], history=history, on_event=on_event,
        parallel_tools=agent.get("parallel", bool(subs)),
        max_steps=agent.get("max_steps"),
    )

    out = agent.get("output")
    saved = None
    if out and final and len(final.strip()) >= 80:
        target = WORKSPACE / out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(final)
        saved = out

    return {"agent": name, "final": final, "saved": saved,
            "is_orchestrator": bool(subs)}
