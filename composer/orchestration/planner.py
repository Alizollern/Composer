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
from composer import companies

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


def _snapshot_files(base):
    return {str(f.relative_to(base)): None
            for f in base.rglob("*")
            if f.is_file() and ".runs" not in f.parts and not f.name.startswith(".")}


def orchestrate_dynamic(goal, orchestrator=None, on_event=None, llm=None, company=None):
    orchestrator = orchestrator or ORCHESTRATOR_AGENT
    llm = llm or ClaudeProvider()
    names = discover_agents()

    base = companies.company_dir(company) if company else WORKSPACE
    base.mkdir(parents=True, exist_ok=True)
    before = set(_snapshot_files(base))

    if orchestrator in names:
        _emit(on_event, type="start", mode="dynamic",
              orchestrator=orchestrator, goal=goal, company=company,
              workers=load_agent(orchestrator).get("subagents") or [])
        res = run_agent_by_name(orchestrator, goal, llm=llm,
                                on_event=on_event, company=company)
        final = res["final"]
    else:
        # синтезируем оркестратора над всеми агентами
        workers = [n for n in names if n != orchestrator]
        _emit(on_event, type="start", mode="dynamic",
              orchestrator="(synthesized)", goal=goal, company=company, workers=workers)
        tools = (make_workspace_tools(base)
                 + make_agent_tools(workers, llm, on_event, workspace_base=base))
        full_goal = companies.profile_context(company) + goal if company else goal
        final = run_agent(full_goal, llm, tools, InMemoryMemory(),
                          system=SYNTH_SYSTEM, on_event=on_event,
                          parallel_tools=True)

    # какие файлы появились в ходе прогона
    after = set(_snapshot_files(base))
    produced = {}
    for name in sorted(after):
        p = base / name
        try:
            produced[name] = p.read_text()
        except Exception:
            produced[name] = "(бинарный файл)"

    _emit(on_event, type="done")
    return {
        "goal": goal,
        "mode": "dynamic",
        "company": company,
        "orchestrator": orchestrator if orchestrator in names else "(synthesized)",
        "final": final,
        "files": produced,
        "new_files": sorted(after - before),
    }
