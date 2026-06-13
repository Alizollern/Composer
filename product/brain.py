"""
brain.py — единственный мост между продуктом Evergreen и движком composer/.

ВЕСЬ продукт обращается к харнессу только отсюда. Если завтра движок переедет
в отдельный пакет/репозиторий — менять придётся один этот файл, а не весь продукт.
Это и есть «шов»: реализация за ним сменная, интерфейс стабильный.

Здесь — тонкие обёртки над публичной поверхностью composer/:
  - выбор провайдера LLM (Claude для прода / Gemini для тестов);
  - запуск одного агента по имени (worker);
  - динамическая оркестрация (агент-оркестратор сам зовёт суб-агентов).

Бизнес-модули (product/modules/*) зовут эти функции, не импортируя composer напрямую.
"""

from composer.engine.providers import get_provider
from composer.orchestration.runner import run_agent_by_name
from composer.orchestration.planner import orchestrate_dynamic

from product.agent_log import log_call, log_event


def provider(name=None, **kwargs):
    """Вернуть LLM-провайдер. По умолчанию — из COMPOSER_PROVIDER (claude|gemini)."""
    return get_provider(name, **kwargs)


def run_agent(agent_name, task, *, company=None, llm=None, on_event=None,
              history=None, output_name=None):
    """Запустить одного агента-воркера по имени и вернуть его результат.

    company — слаг компании (мультитенант: прогон скоупится в её папку/данные).
    Возвращает dict: {"agent", "final", "saved", "is_orchestrator"}.
    """
    with log_call("agent.run", agent=agent_name, company=company, task=task) as ev:
        result = run_agent_by_name(
            agent_name, task, llm=llm, on_event=on_event,
            history=history, company=company, output_name=output_name,
        )
        ev.set_output((result or {}).get("final"))
    return result


def orchestrate(goal, *, company=None, orchestrator=None, llm=None, on_event=None):
    """Динамическая оркестрация: агент-оркестратор сам декомпозирует цель и
    делегирует суб-агентам (в т.ч. параллельно). Возвращает структурированный
    результат с финальным текстом и созданными файлами.
    """
    with log_call("agent.orchestrate", goal=goal, company=company,
                  orchestrator=orchestrator) as ev:
        result = orchestrate_dynamic(
            goal, orchestrator=orchestrator, on_event=on_event,
            llm=llm, company=company,
        )
        ev.set_output((result or {}).get("final"))
    return result


def complete(system, user, *, llm=None, operation="complete", company=None):
    """Один контролируемый вызов LLM без агентного цикла и без инструментов.

    Нужен там, где продукту требуется ПРЕДСКАЗУЕМЫЙ ответ по строгому контракту,
    а не самостоятельная работа агента, — прежде всего строгий RAG чат-бота (M2):
    «ответь только по этим фрагментам и сошлись на источник». Возвращает текст.

    llm — провайдер (для тестов можно подменить фейком); по умолчанию берётся
    из окружения (claude|gemini).

    Каждый вызов попадает в журнал агента (product/agent_log): видно system-
    инструкцию, вход и ответ модели — это и есть «мысли» ИИ для контроля.
    """
    llm = llm or get_provider()
    messages = [{"role": "user", "content": user}]
    with log_call("llm.complete", operation=operation, company=company,
                  system=system, prompt=user) as ev:
        result = llm.call(system, messages, [])
        text = (result.get("text") or "").strip()
        ev.set_output(text)
    return text
