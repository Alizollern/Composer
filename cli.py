"""
Composer AI — терминальный интерфейс (для разработки/проверки без фронта).

  python3 cli.py agents                       — список агентов
  python3 cli.py run "цель руководителя"      — прогнать пайплайн
  python3 cli.py chat employee_assistant      — чат с агентом
"""

import sys

from composer.engine.providers import ClaudeProvider
from composer.engine.memory import JSONMemory
from composer.engine.loop import run_agent
from composer.agents.loader import discover_agents, load_agent
from composer.orchestration.orchestrator import orchestrate
from composer.config import WORKSPACE


def render(event):
    """Рендер событий движка в терминал."""
    t = event.get("type")
    if t == "start":
        print(f"🎯 {event['goal']}\n🔗 {' → '.join(event['pipeline'])}")
    elif t == "phase":
        print(f"\n{'=' * 60}\n  АГЕНТ: {event['agent']}\n{'=' * 60}")
    elif t == "text":
        print(f"\n🤖 {event['text']}")
    elif t == "tool_call":
        print(f"   🔧 {event['name']}({event['input']})")
    elif t == "saved":
        print(f"\n  💾 сохранено в workspace/{event['file']} ({event['size']} симв.)")
    elif t == "done":
        print(f"\nГотово. Результаты — в {WORKSPACE}")


def cmd_run(goal):
    orchestrate(goal, on_event=render)


def cmd_chat(name):
    if name not in discover_agents():
        print(f"Нет агента «{name}». Доступные: {', '.join(discover_agents())}")
        return
    agent = load_agent(name)
    llm = ClaudeProvider()
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
        print("Агенты:", ", ".join(discover_agents()))
    elif cmd == "run":
        cmd_run(" ".join(args[1:]) or "создать стандарты обслуживания на основе Starbucks")
    elif cmd == "chat":
        cmd_chat(args[1] if len(args) > 1 else "employee_assistant")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
