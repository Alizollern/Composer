"""
Динамическая оркестрация (главный режим платформы).

В отличие от линейного pipeline.txt, здесь оркестратор-АГЕНТ сам решает, каких
суб-агентов и в каком порядке/параллельно звать, исходя из цели. Это и есть
"harness as infrastructure": добавил агентов-воркеров — оркестратор их подхватил.

Если агента-оркестратора нет в agents/, он синтезируется на лету: ему отдаются
все остальные агенты как суб-агенты.
"""

from composer.config import WORKSPACE, ORCHESTRATOR_AGENT
from composer.engine.providers import ClaudeProvider
from composer.engine.memory import InMemoryMemory
from composer.engine.loop import run_agent
from composer.agents.loader import discover_agents, load_agent
from composer.orchestration.agent_tools import make_agent_tools
from composer.tools.registry import make_workspace_tools
from composer.orchestration.runner import run_agent_by_name

SYNTH_SYSTEM = (
    "Ты — оркестратор платформы Composer AI. Тебе дана цель пользователя.\n"
    "У тебя есть инструменты delegate_to_<агент> — это специализированные агенты.\n"
    "Декомпозируй цель на подзадачи и делегируй их подходящим агентам. Чтобы они "
    "работали ПАРАЛЛЕЛЬНО — вызови несколько delegate_*-инструментов в одном ходе.\n"
    "Сам работу суб-агентов не выполняй. В конце собери их результаты в единый, "
    "связный итог для пользователя."
)


def _emit(on_event, **event):
    if on_event:
        on_event(event)


def _snapshot_files():
    return {str(f.relative_to(WORKSPACE)): None
            for f in WORKSPACE.rglob("*")
            if f.is_file() and ".runs" not in f.parts and not f.name.startswith(".")}


def orchestrate_dynamic(goal, orchestrator=None, on_event=None, llm=None):
    orchestrator = orchestrator or ORCHESTRATOR_AGENT
    llm = llm or ClaudeProvider()
    names = discover_agents()

    before = set(_snapshot_files())

    if orchestrator in names:
        _emit(on_event, type="start", mode="dynamic",
              orchestrator=orchestrator, goal=goal,
              workers=load_agent(orchestrator).get("subagents") or [])
        res = run_agent_by_name(orchestrator, goal, llm=llm, on_event=on_event)
        final = res["final"]
    else:
        # синтезируем оркестратора над всеми агентами
        workers = [n for n in names if n != orchestrator]
        _emit(on_event, type="start", mode="dynamic",
              orchestrator="(synthesized)", goal=goal, workers=workers)
        tools = make_workspace_tools() + make_agent_tools(workers, llm, on_event)
        final = run_agent(goal, llm, tools, InMemoryMemory(),
                          system=SYNTH_SYSTEM, on_event=on_event,
                          parallel_tools=True)

    # какие файлы появились в ходе прогона
    after = set(_snapshot_files())
    produced = {}
    for name in sorted(after):
        p = WORKSPACE / name
        try:
            produced[name] = p.read_text()
        except Exception:
            produced[name] = "(бинарный файл)"

    _emit(on_event, type="done")
    return {
        "goal": goal,
        "mode": "dynamic",
        "orchestrator": orchestrator if orchestrator in names else "(synthesized)",
        "final": final,
        "files": produced,
        "new_files": sorted(after - before),
    }
