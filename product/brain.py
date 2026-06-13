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
from composer.engine.structured import complete_json as _engine_complete_json
from composer.engine.loop import run_agent as _engine_run_agent
from composer.engine.memory import InMemoryMemory
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


def run_tools_agent(system, task, tools, *, llm=None, max_steps=None,
                    on_event=None, history=None, company=None,
                    operation="tools_agent"):
    """Многошаговый агент с ПРОДУКТОВЫМИ инструментами.

    В отличие от run_agent (агент из папки composer) и complete (одиночный вызов),
    здесь инструменты собирает САМ продукт и передаёт их движку: это и есть «руки»
    для движка — он умеет искать по стандартам, читать отзывы и т.п. через
    callable-инструменты Evergreen, не зная ничего о домене.

    tools — список {"schema": {...}, "fn": callable(input_dict) -> str}.
    Движок крутит цикл: модель думает → зовёт инструмент → получает результат →
    … → финальный ответ. Возвращает текст финального ответа.
    """
    llm = llm or get_provider()
    with log_call("agent.tools", operation=operation, company=company,
                  task=task) as ev:
        final = _engine_run_agent(
            task, llm, tools, InMemoryMemory(),
            system=system, max_steps=max_steps, on_event=on_event,
            history=history, parallel_tools=False,
        )
        ev.set_output(final)
    return final


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


def complete_json(system, user, *, expect="any", retries=1, llm=None,
                  operation="complete_json", company=None):
    """Контролируемый вызов LLM, который ОБЯЗАН вернуть валидный JSON.

    Возвращает уже разобранный Python-объект (dict/list — по `expect`). Если
    модель ломает формат, движок переспрашивает её до `retries` раз с описанием
    ошибки. Нужен везде, где продукту важен строгий контракт, а не свободный
    текст: разбор отзыва, генерация теста, классификация.

    Внутри строится поверх complete(), поэтому каждый вызов так же попадает в
    журнал агента и так же подменяется фейком в тестах.
    """
    def _fn(sys_text, usr_text):
        return complete(sys_text, usr_text, llm=llm, operation=operation,
                        company=company)

    data, _text = _engine_complete_json(_fn, system, user,
                                        expect=expect, retries=retries)
    return data
