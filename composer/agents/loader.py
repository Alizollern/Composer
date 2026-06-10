"""
Загрузчик агентов. Агент = ПАПКА agents/<имя>/, а не код.

  agents/<имя>/
    role.md          — кто агент и что делает (system-промпт)
    skills/*.md      — навыки (склеиваются в промпт)
    knowledge/...     — личная база знаний (приватный RAG)
    agent.json       — (опц.) манифест; перекрывает tools.txt/output.txt:
        {
          "description": "...",
          "model": "claude-...",          # переопределить модель
          "web": true,                     # подключить веб-поиск
          "integrations": ["http_request"],# интеграции из реестра
          "subagents": ["researcher", ...],# делает агента ОРКЕСТРАТОРОМ
          "parallel": true,                # выполнять делегирования параллельно
          "output": "result.md"            # детерминированно сохранить результат
        }
    tools.txt        — (опц., legacy) "web_search" → веб-инструменты
    output.txt       — (опц., legacy) имя файла-результата

Фронтенд может СОЗДАВАТЬ агентов через create_agent() — код менять не нужно.
"""

import json

from composer.config import AGENTS_DIR, KNOWLEDGE_DIR
from composer.tools.registry import (
    make_workspace_tools, make_knowledge_tools, make_web_search,
)
from composer.tools.base import get_integration_tools

BASE_PREAMBLE = (
    "Ты — специализированный агент платформы Composer AI.\n"
    "Доступные инструменты:\n"
    "- общие рабочие файлы (workspace) — обмен результатами с другими агентами;\n"
    "- собственная база знаний (knowledge) — твой приватный источник правды;\n"
    "- возможно, веб-поиск, интеграции и делегирование суб-агентам.\n"
    "Активно пользуйся инструментами. Действуй строго по своей роли ниже.\n"
)

ORCHESTRATOR_HINT = (
    "\n\n## ТЫ — ОРКЕСТРАТОР\n"
    "У тебя есть инструменты delegate_to_<агент>. Декомпозируй цель на подзадачи "
    "и делегируй их подходящим суб-агентам. Чтобы они работали ПАРАЛЛЕЛЬНО — "
    "вызови несколько delegate_*-инструментов в одном ходе. Затем собери их "
    "результаты в единый итог. Не делай работу суб-агентов сам.\n"
)


def _read(path):
    return path.read_text() if path.exists() else ""


def _manifest(folder):
    f = folder / "agent.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            return {}
    return {}


def discover_agents():
    if not AGENTS_DIR.is_dir():
        return []
    return [d.name for d in sorted(AGENTS_DIR.iterdir()) if d.is_dir()]


def load_agent(name):
    folder = AGENTS_DIR / name
    if not folder.is_dir():
        raise FileNotFoundError(f"Нет агента с папкой: agents/{name}")

    man = _manifest(folder)
    role = _read(folder / "role.md")

    skills_dir = folder / "skills"
    skills = []
    if skills_dir.is_dir():
        for f in sorted(skills_dir.glob("*.md")):
            skills.append(f"### Навык: {f.stem}\n{f.read_text()}")

    system = BASE_PREAMBLE + "\n## ТВОЯ РОЛЬ\n" + role
    if skills:
        system += "\n\n## ТВОИ НАВЫКИ (SKILLS)\n" + "\n\n".join(skills)

    subagents = man.get("subagents") or []
    if subagents:
        system += ORCHESTRATOR_HINT

    # --- Инструменты ---
    # Корни базы знаний: приватная папка агента + общие домены из knowledge/.
    knowledge_refs = man.get("knowledge_refs") or []
    roots = [("self", folder / "knowledge")]
    for ref in knowledge_refs:
        roots.append((ref, KNOWLEDGE_DIR / ref))
    tools = make_workspace_tools() + make_knowledge_tools(roots)

    # web: из манифеста или legacy tools.txt
    cfg = folder / "tools.txt"
    has_web = bool(man.get("web")) or (cfg.exists() and "web_search" in cfg.read_text())
    if has_web:
        tools += make_web_search()

    # интеграции из реестра
    integrations = man.get("integrations") or []
    if integrations:
        tools += get_integration_tools(integrations)

    # output: из манифеста или legacy output.txt
    output = man.get("output")
    if not output:
        of = folder / "output.txt"
        output = of.read_text().strip() if of.exists() else None

    return {
        "name": name,
        "system": system,
        "tools": tools,
        "folder": folder,
        "output": output,
        "model": man.get("model"),
        "subagents": subagents,
        "integrations": integrations,
        "web": has_web,
        "parallel": man.get("parallel", bool(subagents)),
        "max_steps": man.get("max_steps"),
        "knowledge_refs": knowledge_refs,
    }


def describe_agent(name):
    """Краткая карточка агента для фронтенда (без сборки инструментов)."""
    folder = AGENTS_DIR / name
    man = _manifest(folder)
    role = _read(folder / "role.md")
    first_line = next((l.strip() for l in role.splitlines() if l.strip()), "")
    skills = [f.stem for f in (folder / "skills").glob("*.md")] \
        if (folder / "skills").is_dir() else []
    cfg = folder / "tools.txt"
    has_web = bool(man.get("web")) or (cfg.exists() and "web_search" in cfg.read_text())
    output = man.get("output")
    if not output:
        of = folder / "output.txt"
        output = of.read_text().strip() if of.exists() else None
    subagents = man.get("subagents") or []
    return {
        "name": name,
        "description": man.get("description") or first_line,
        "skills": skills,
        "web": has_web,
        "integrations": man.get("integrations") or [],
        "subagents": subagents,
        "is_orchestrator": bool(subagents),
        "model": man.get("model"),
        "output": output,
        "knowledge_refs": man.get("knowledge_refs") or [],
    }


def create_agent(name, role, skills=None, knowledge=None, web=False,
                 output=None, integrations=None, subagents=None,
                 model=None, parallel=None, description=None,
                 knowledge_refs=None):
    """Создать/обновить агента (используется фронтендом).

    skills / knowledge — dict имя->текст. Манифест agent.json пишется, если
    заданы расширенные поля (integrations / subagents / model / ...).
    """
    folder = AGENTS_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "role.md").write_text(role)

    if skills:
        sd = folder / "skills"
        sd.mkdir(exist_ok=True)
        for fname, content in skills.items():
            (sd / f"{fname}.md").write_text(content)

    if knowledge:
        kd = folder / "knowledge"
        kd.mkdir(exist_ok=True)
        for fname, content in knowledge.items():
            (kd / fname).write_text(content)

    man = {}
    if description:
        man["description"] = description
    if web:
        man["web"] = True
    if output:
        man["output"] = output
    if integrations:
        man["integrations"] = integrations
    if subagents:
        man["subagents"] = subagents
    if model:
        man["model"] = model
    if parallel is not None:
        man["parallel"] = parallel
    if knowledge_refs:
        man["knowledge_refs"] = knowledge_refs
    if man:
        (folder / "agent.json").write_text(
            json.dumps(man, ensure_ascii=False, indent=2))

    return describe_agent(name)
