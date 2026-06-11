"""
Оркестратор — динамический конвейер агентов.

Не содержит зашитых агентов. Читает порядок из pipeline.txt, грузит каждого
агента из его папки, прогоняет через run_agent и САМ сохраняет финальный
ответ агента в его файл-результат (детерминированно — не зависим от того,
вызвал ли агент write_file).

orchestrate() отдаёт структурированный результат и эмитит события (on_event),
чтобы CLI/в API можно было показывать прогресс.
"""

from composer.config import WORKSPACE, PIPELINE_FILE, MEMORY_FILE
from composer.engine.providers import get_provider
from composer.engine.memory import JSONMemory
from composer.engine.loop import run_agent
from composer.agents.loader import load_agent, discover_agents


def load_pipeline():
    if PIPELINE_FILE.exists():
        lines = [l.strip() for l in PIPELINE_FILE.read_text().splitlines()]
        return [l for l in lines if l and not l.startswith("#")]
    return discover_agents()


def set_pipeline(order):
    PIPELINE_FILE.write_text("\n".join(order) + "\n")
    return load_pipeline()


def _emit(on_event, **event):
    if on_event:
        on_event(event)


def orchestrate(goal, on_event=None, llm=None):
    llm = llm or get_provider()
    memory = JSONMemory(MEMORY_FILE)
    pipeline = load_pipeline()

    _emit(on_event, type="start", goal=goal, pipeline=pipeline)
    results = {"goal": goal, "pipeline": pipeline, "agents": [], "files": {}}

    for name in pipeline:
        agent = load_agent(name)
        _emit(on_event, type="phase", agent=name)

        final = run_agent(
            f"Цель руководителя: «{goal}». Выполни свою роль до конца.",
            llm, agent["tools"], memory, system=agent["system"], on_event=on_event,
        )

        out = agent.get("output")
        saved = None
        if out and final and len(final.strip()) >= 100:
            target = WORKSPACE / out
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(final)
            saved = out
            results["files"][out] = final
            _emit(on_event, type="saved", agent=name, file=out, size=len(final))

        results["agents"].append({"name": name, "final": final, "saved": saved})

    _emit(on_event, type="done")
    return results
