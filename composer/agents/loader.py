"""
Загрузчик агентов. Агент = ПАПКА agents/<имя>/, а не код.

  agents/<имя>/
    role.md          — кто агент и что делает (system-промпт)
    skills/*.md      — навыки (склеиваются в промпт)
    knowledge/...     — личная база знаний (приватный RAG)
    tools.txt        — (опц.) "web_search" → добавить веб-инструменты
    output.txt       — (опц.) имя файла-результата в workspace/

Фронтенд может СОЗДАВАТЬ агентов через create_agent() — код менять не нужно.
"""

from composer.config import AGENTS_DIR
from composer.tools.registry import (
    make_workspace_tools, make_knowledge_tools, make_web_search,
)

BASE_PREAMBLE = (
    "Ты — специализированный агент платформы Composer AI.\n"
    "Доступные инструменты:\n"
    "- общие рабочие файлы (workspace) — обмен результатами с другими агентами;\n"
    "- собственная база знаний (knowledge) — твой приватный источник правды;\n"
    "- возможно, веб-поиск и чтение страниц.\n"
    "Активно пользуйся инструментами. Действуй строго по своей роли ниже.\n"
)


def discover_agents():
    if not AGENTS_DIR.is_dir():
        return []
    return [d.name for d in sorted(AGENTS_DIR.iterdir()) if d.is_dir()]


def load_agent(name):
    folder = AGENTS_DIR / name
    if not folder.is_dir():
        raise FileNotFoundError(f"Нет агента с папкой: agents/{name}")

    role = (folder / "role.md").read_text() if (folder / "role.md").exists() else ""

    skills_dir = folder / "skills"
    skills = []
    if skills_dir.is_dir():
        for f in sorted(skills_dir.glob("*.md")):
            skills.append(f"### Навык: {f.stem}\n{f.read_text()}")

    system = BASE_PREAMBLE + "\n## ТВОЯ РОЛЬ\n" + role
    if skills:
        system += "\n\n## ТВОИ НАВЫКИ (SKILLS)\n" + "\n\n".join(skills)

    knowledge_dir = folder / "knowledge"
    tools = make_workspace_tools() + make_knowledge_tools(knowledge_dir)

    cfg = folder / "tools.txt"
    has_web = cfg.exists() and "web_search" in cfg.read_text()
    if has_web:
        tools += make_web_search()

    out_file = folder / "output.txt"
    output = out_file.read_text().strip() if out_file.exists() else None

    return {"name": name, "system": system, "tools": tools,
            "folder": folder, "output": output}


def describe_agent(name):
    """Краткая карточка агента для фронтенда (без сборки инструментов)."""
    folder = AGENTS_DIR / name
    role = (folder / "role.md").read_text() if (folder / "role.md").exists() else ""
    first_line = next((l.strip() for l in role.splitlines() if l.strip()), "")
    skills = [f.stem for f in (folder / "skills").glob("*.md")] if (folder / "skills").is_dir() else []
    cfg = folder / "tools.txt"
    has_web = cfg.exists() and "web_search" in cfg.read_text()
    out_file = folder / "output.txt"
    output = out_file.read_text().strip() if out_file.exists() else None
    return {"name": name, "description": first_line, "skills": skills,
            "web": has_web, "output": output}


def create_agent(name, role, skills=None, knowledge=None, web=False, output=None):
    """Создать/обновить агента (используется фронтендом). skills/knowledge — dict имя->текст."""
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

    if web:
        (folder / "tools.txt").write_text("web_search\n")
    if output:
        (folder / "output.txt").write_text(output + "\n")

    return describe_agent(name)
