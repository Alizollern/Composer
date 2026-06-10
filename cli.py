"""
Composer AI — терминальный интерфейс (для разработки/проверки без фронта).

  python3 cli.py agents                         — список агентов
  python3 cli.py integrations                   — список интеграций (плагинов)
  python3 cli.py orchestrate "цель"             — динамическая оркестрация (главный режим)
  python3 cli.py run "цель"                     — линейный пайплайн (legacy)
  python3 cli.py agent <имя> "задача"           — запустить одного агента
  python3 cli.py chat <имя>                     — чат с агентом
"""

import sys

from composer.engine.providers import ClaudeProvider
from composer.engine.memory import JSONMemory
from composer.engine.loop import run_agent
from composer.agents.loader import discover_agents, load_agent, describe_agent
from composer.tools.base import list_integrations
from composer.orchestration.orchestrator import orchestrate
from composer.orchestration.planner import orchestrate_dynamic
from composer.orchestration.runner import run_agent_by_name
from composer.config import WORKSPACE


def render(event):
    """Рендер событий движка в терминал."""
    t = event.get("type")
    depth = event.get("depth", 0)
    pad = "    " * depth
    if t == "start":
        mode = event.get("mode", "")
        print(f"🎯 {event['goal']}")
        if event.get("workers"):
            print(f"🧩 оркестратор [{mode}] → воркеры: {', '.join(event['workers'])}")
        elif event.get("pipeline"):
            print(f"🔗 {' → '.join(event['pipeline'])}")
    elif t == "phase":
        print(f"\n{'=' * 60}\n  АГЕНТ: {event['agent']}\n{'=' * 60}")
    elif t == "subagent_start":
        print(f"\n{pad}┌─ ▶ делегирую → {event['agent']}: {event['task'][:80]}")
    elif t == "subagent_done":
        print(f"{pad}└─ ✅ {event['agent']} готов ({event['size']} симв.)")
    elif t == "text":
        if event.get("text", "").strip():
            print(f"\n{pad}🤖 {event['text']}")
    elif t == "tool_call":
        print(f"{pad}   🔧 {event['name']}({_short(event['input'])})")
    elif t == "saved":
        print(f"\n  💾 сохранено в workspace/{event['file']} ({event['size']} симв.)")
    elif t == "done":
        print(f"\nГотово. Результаты — в {WORKSPACE}")


def _short(obj):
    s = str(obj)
    return s if len(s) <= 100 else s[:100] + "…"


def cmd_orchestrate(goal):
    res = orchestrate_dynamic(goal, on_event=render)
    print(f"\n{'=' * 60}\nИТОГ:\n{res['final']}")
    if res.get("new_files"):
        print(f"\nНовые файлы: {', '.join(res['new_files'])}")


def cmd_run(goal):
    orchestrate(goal, on_event=render)


def cmd_agent(name, task):
    if name not in discover_agents():
        print(f"Нет агента «{name}». Доступные: {', '.join(discover_agents())}")
        return
    res = run_agent_by_name(name, task, on_event=render)
    print(f"\n{'=' * 60}\nРЕЗУЛЬТАТ ({name}):\n{res['final']}")


def cmd_chat(name):
    if name not in discover_agents():
        print(f"Нет агента «{name}». Доступные: {', '.join(discover_agents())}")
        return
    agent = load_agent(name)
    llm = ClaudeProvider(model=agent.get("model"))
    memory = JSONMemory(WORKSPACE.parent / f"memory_chat_{name}.json")
    history = []
    print(f"💬 Чат с «{name}». Пиши вопрос (или 'exit').\n")
    while True:
        try:
            msg = input("👤 ты: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in {"exit", "quit", "выход"}:
            break
        if not msg:
            continue
        run_agent(msg, llm, agent["tools"], memory,
                  system=agent["system"], history=history, on_event=render)
        print()


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "agents":
        for n in discover_agents():
            d = describe_agent(n)
            tag = " [оркестратор]" if d["is_orchestrator"] else ""
            print(f"- {n}{tag}: {d['description']}")
    elif cmd == "integrations":
        for it in list_integrations():
            print(f"- {it['name']} [{it['category']}]: {it['description']}")
    elif cmd == "orchestrate":
        cmd_orchestrate(" ".join(args[1:]) or "Сделай краткий обзор рынка кофеен в Алматы")
    elif cmd == "run":
        cmd_run(" ".join(args[1:]) or "создать стандарты обслуживания на основе Starbucks")
    elif cmd == "agent":
        if len(args) < 3:
            print("Использование: python3 cli.py agent <имя> \"задача\"")
            return
        cmd_agent(args[1], " ".join(args[2:]))
    elif cmd == "chat":
        cmd_chat(args[1] if len(args) > 1 else "employee_assistant")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
