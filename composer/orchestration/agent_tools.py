"""
Делегирование: агент как инструмент (agent-as-tool).

make_agent_tools() превращает список агентов в набор инструментов
delegate_to_<имя>. Когда оркестратор вызывает такой инструмент, внутри
запускается полноценный run_agent суб-агента и возвращается его результат.

Если оркестратор вызывает несколько delegate_*-инструментов за один ход и у него
parallel=True — суб-агенты исполняются ОДНОВРЕМЕННО (см. loop.run_agent).

Поддерживается вложенность (суб-агент сам может быть оркестратором) с защитой
по глубине MAX_DELEGATION_DEPTH.
"""

from pathlib import Path

from composer.config import WORKSPACE, MAX_DELEGATION_DEPTH
from composer.engine.loop import run_agent
from composer.engine.memory import InMemoryMemory


def make_agent_tools(worker_names, llm, on_event=None, depth=0, workspace_base=None):
    return [_make_one(name, llm, on_event, depth, workspace_base) for name in worker_names]


def _make_one(name, llm, on_event, depth, workspace_base=None):
    from composer.agents.loader import load_agent, describe_agent

    try:
        desc = describe_agent(name).get("description", "")
    except Exception:
        desc = ""

    def fn(inp):
        task = inp.get("task", "")
        agent = load_agent(name, workspace_base=workspace_base)
        tools = list(agent["tools"])

        # вложенное делегирование (с защитой по глубине)
        subs = agent.get("subagents") or []
        if subs and depth + 1 < MAX_DELEGATION_DEPTH:
            tools += make_agent_tools(subs, llm, on_event, depth + 1, workspace_base)

        def child_emit(ev):
            tagged = dict(ev)
            tagged.setdefault("agent", name)
            tagged.setdefault("depth", depth + 1)
            if on_event:
                on_event(tagged)

        if on_event:
            on_event({"type": "subagent_start", "agent": name,
                      "task": task, "depth": depth + 1})

        final = run_agent(
            task, llm, tools, InMemoryMemory(),
            system=agent["system"], on_event=child_emit,
            parallel_tools=agent.get("parallel", False),
            max_steps=agent.get("max_steps"),
        )

        # детерминированно сохраняем результат суб-агента, если у него есть output
        out = agent.get("output")
        if out and final and len(final.strip()) >= 80:
            base = Path(workspace_base) if workspace_base else WORKSPACE
            target = base / out
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(final)

        if on_event:
            on_event({"type": "subagent_done", "agent": name,
                      "depth": depth + 1, "size": len(final or "")})
        return final

    return {
        "schema": {
            "name": f"delegate_to_{name}",
            "description": (f"Делегировать подзадачу агенту «{name}». {desc} "
                            "Передай конкретную задачу в поле task."),
            "input_schema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string",
                             "description": "Конкретная подзадача для этого агента"},
                },
                "required": ["task"],
            },
        },
        "fn": fn,
    }
