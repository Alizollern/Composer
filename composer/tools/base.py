"""
Реестр интеграций (плагины-инструменты).

Это точка роста проекта: чтобы добавить интеграцию (Slack, Notion, CRM, любой
REST API) — кладёшь файл в composer/tools/integrations/ и вешаешь декоратор
@integration. Он сам регистрируется здесь. Код ядра при этом НЕ меняется.

    from composer.tools.base import integration

    @integration(
        name="my_tool",
        description="Что делает инструмент (для модели).",
        input_schema={"type": "object", "properties": {...}, "required": [...]},
    )
    def my_tool(inp: dict) -> str:
        ...
        return "результат"

Агент получает интеграцию, указав её имя в agent.json -> "integrations": ["my_tool"].
"""

from importlib import import_module
import pkgutil

# name -> {"schema": {...}, "fn": callable, "category": str}
_REGISTRY = {}
_LOADED = False


def integration(name, description, input_schema, category="general"):
    """Декоратор: регистрирует функцию-инструмент в глобальном реестре."""
    def deco(fn):
        _REGISTRY[name] = {
            "schema": {"name": name, "description": description,
                       "input_schema": input_schema},
            "fn": fn,
            "category": category,
        }
        return fn
    return deco


def _ensure_loaded():
    """Лениво импортирует все модули из integrations/, чтобы они зарегистрировались."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    from composer.tools import integrations as pkg
    for _, modname, _is_pkg in pkgutil.iter_modules(pkg.__path__):
        import_module(f"{pkg.__name__}.{modname}")


def list_integrations():
    """Карточки всех доступных интеграций (для фронтенда)."""
    _ensure_loaded()
    return [{"name": n, "description": t["schema"]["description"],
             "category": t["category"]}
            for n, t in sorted(_REGISTRY.items())]


def get_integration_tools(names):
    """Вернуть инструменты по списку имён (для сборки агента)."""
    _ensure_loaded()
    return [_REGISTRY[n] for n in (names or []) if n in _REGISTRY]
