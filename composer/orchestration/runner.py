"""
Раннер одного агента по имени.

Универсальная точка запуска: грузит агента из папки, при наличии subagents
подключает инструменты делегирования (тогда агент работает как оркестратор),
прогоняет run_agent и детерминированно сохраняет результат.

Контекст компании (company): прогон скоупится на папку компании —
агент читает/пишет внутри неё, профиль компании подмешивается в задачу,
а итоговый документ сохраняется туда же отдельным файлом.
"""

import re
import time

from composer.config import WORKSPACE
from composer.engine.providers import ClaudeProvider
from composer.engine.memory import InMemoryMemory
from composer.engine.loop import run_agent
from composer.agents.loader import load_agent
from composer.orchestration.agent_tools import make_agent_tools
from composer import companies


def _doc_name(task, fallback="result"):
    """Имя файла-результата из текста задачи: дата + короткий слаг."""
    words = re.sub(r"[^\w\s-]", "", (task or "").lower(), flags=re.UNICODE).split()
    slug = "-".join(words[:6]).strip("-") or fallback
    return f"{time.strftime('%Y-%m-%d')}_{slug[:60]}.md"


def _unique(base_dir, name):
    target = base_dir / name
    if not target.exists():
        return target
    stem, _, ext = name.rpartition(".")
    n = 2
    while (base_dir / f"{stem}-{n}.{ext}").exists():
        n += 1
    return base_dir / f"{stem}-{n}.{ext}"


def run_agent_by_name(name, task, llm=None, on_event=None,
                      memory=None, history=None, company=None,
                      output_name=None):
    base = companies.company_dir(company) if company else WORKSPACE
    base.mkdir(parents=True, exist_ok=True)

    agent = load_agent(name, workspace_base=base)
    llm = llm or ClaudeProvider(model=agent.get("model"))

    # подмешиваем профиль компании в задачу
    full_task = companies.profile_context(company) + task if company else task

    tools = list(agent["tools"])
    subs = agent.get("subagents") or []
    if subs:
        tools += make_agent_tools(subs, llm, on_event, workspace_base=base)

    final = run_agent(
        full_task, llm, tools, memory or InMemoryMemory(),
        system=agent["system"], history=history, on_event=on_event,
        parallel_tools=agent.get("parallel", bool(subs)),
        max_steps=agent.get("max_steps"),
    )

    saved = None
    if final and len(final.strip()) >= 80:
        # имя файла: явно заданное -> output из манифеста -> производное от задачи
        fname = output_name or agent.get("output") or _doc_name(task)
        # в контексте компании итог НЕ перезаписывает, а добавляется как новый док
        target = _unique(base, fname) if company else (base / fname)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(final)
        saved = str(target.relative_to(base))

    return {"agent": name, "final": final, "saved": saved,
            "is_orchestrator": bool(subs)}
