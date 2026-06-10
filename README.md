# Composer AI

> **Для людей и для агентов.** Этот файл — единый источник правды о проекте.
> Если ты ИИ-агент, который зашёл в репозиторий: прочитай README целиком — здесь
> описано, что это за проект, как он устроен, как его запускать и как его расширять,
> не меняя ядро.

---

## 1. Что это за проект

**Composer AI** — платформа, которая позволяет **не-разработчику создавать ИИ-агентов**.
Идея: *«harness as infrastructure»* — пользователь пишет промпт и описание роли, а
вся архитектура (вызов модели, цикл рассуждения, память, инструменты, оркестрация)
уже готова на платформе. Человек не пишет код — он **добавляет папку с агентом**.

### Текущая вертикаль (то, что реализовано сейчас)

Первая узкая ниша для MVP/питча — **«Цифровой двойник CEO» для сети кофеен**
(демо-клиент: **АлматыКофе**, 3 филиала, Казахстан). Это пайплайн из
специализированных агентов, которые:

1. **Создают стандарты обслуживания** — читают стандарты мировых брендов
   (Starbucks, McDonald's и т.д.) **из интернета** и адаптируют под клиента.
2. **Редактируют/обновляют стандарты** при появлении новых данных.
3. **Советуют decision-maker'у** (поддержка управленческих решений).
4. **Псевдо-GPT для сотрудников** — чат, где сотрудник может спросить про стандарты
   и рабочие моменты.

У каждого агента — **свои навыки (skills) и своя база знаний (knowledge)**.

---

## 2. Архитектура: 4 «шва» (seams)

Ядро построено на четырёх абстракциях. Каждую можно заменить, не трогая остальные.

| # | Шов | Где | Что делает |
|---|-----|-----|------------|
| 1 | **LLM-провайдер** | `composer/engine/providers.py` | Абстракция над моделью. `LLMProvider` (ABC) → `ClaudeProvider`. Нормализует ответ к `{"text", "tool_calls", "stop_reason", "raw_content"}`. Фабрика `get_provider(name)`. |
| 2 | **Цикл агента** | `composer/engine/loop.py` | `run_agent(...)` — цикл «модель → инструменты → модель», пока не закончит. Эмитит **события** через `on_event`. |
| 3 | **Память** | `composer/engine/memory.py` | `Memory` (ABC) → `JSONMemory(path)`. Read/write истории. |
| 4 | **Инструменты** | `composer/tools/registry.py` | Подключаемые тулзы: workspace-файлы, база знаний, веб-поиск. |

### Событийный движок = адаптивность

`run_agent` не печатает в консоль — он **эмитит события** (`{"type": "text" / "tool_call" / "tool_result" / ...}`)
через колбэк `on_event`. Благодаря этому **один и тот же движок** обслуживает:
- **CLI** (`cli.py` → `render(event)` печатает в терминал),
- **API** (`composer/api/app.py` → события копятся в `RUNS[run_id]["events"]`, фронт их поллит).

### Оркестратор (паттерн orchestrator-worker)

`composer/orchestration/orchestrator.py`:
- `load_pipeline()` / `set_pipeline(order)` — порядок агентов читается из `pipeline.txt`.
- `orchestrate(goal, on_event=None, llm=None)` — прогоняет агентов по очереди, возвращает
  `{"goal", "pipeline", "agents", "files"}`.
- **Детерминированное сохранение результата:** оркестратор сам пишет финальный текст
  агента в файл из `output.txt` (если текст ≥ 100 символов). Это убирает зависимость
  от того, вызовет ли модель `write_file`. Агенты обмениваются результатами через файлы
  в `workspace/` (паттерн «blackboard / references-not-content»).

### Раскладка пакета

```
composer-ai/
├── composer/                      # ← ЯДРО (код менять только здесь)
│   ├── config.py                  # пути, MODEL, MAX_TOKENS, MAX_STEPS (через env)
│   ├── engine/
│   │   ├── providers.py           # Шов 1: LLM-провайдер
│   │   ├── loop.py                # Шов 2: run_agent + события
│   │   └── memory.py              # Шов 3: память
│   ├── tools/
│   │   └── registry.py            # Шов 4: workspace / knowledge / web-инструменты
│   ├── agents/
│   │   └── loader.py              # discover/load/describe/create агентов из ПАПОК
│   ├── orchestration/
│   │   └── orchestrator.py        # пайплайн + детерминированное сохранение
│   └── api/
│       └── app.py                 # FastAPI REST для фронта (Lovable)
│
├── agents/                        # ← ДАННЫЕ (агенты = папки, не код)
│   ├── standards_creator/
│   ├── standards_editor/
│   ├── advisor/
│   └── employee_assistant/
│
├── workspace/                     # результаты работы агентов (в .gitignore)
├── pipeline.txt                   # порядок агентов в пайплайне
├── cli.py                         # терминальный интерфейс
└── requirements.txt
```

---

## 3. Агент = папка (как добавить нового, не трогая код)

Агенты **не захардкожены**. Чтобы добавить агента — создай папку `agents/<имя>/`:

```
agents/<имя>/
├── role.md          # кто агент и что делает (становится system-промптом)
├── skills/*.md      # навыки — каждый .md склеивается в промпт под заголовком навыка
├── knowledge/...     # приватная база знаний агента (его «источник правды»)
├── tools.txt        # (опц.) строка "web_search" → подключить веб-поиск + чтение страниц
└── output.txt       # (опц.) имя файла-результата в workspace/ (напр. standards.md)
```

`composer/agents/loader.py` собирает из этого system-промпт и набор инструментов:
- `discover_agents()` — список имён (= имена папок).
- `load_agent(name)` — собирает `{"name", "system", "tools", "folder", "output"}`.
  System = `BASE_PREAMBLE` + `role.md` + все `skills/*.md`. Всегда есть workspace- и
  knowledge-инструменты; web-инструменты добавляются, если в `tools.txt` есть `web_search`.
- `describe_agent(name)` — карточка для фронта: `{name, description, skills, web, output}`.
- `create_agent(name, role, skills, knowledge, web, output)` — **фронт создаёт агента**
  через API, файлы пишутся на диск автоматически.

### Текущие агенты

| Агент | Роль | web | output | skills |
|-------|------|-----|--------|--------|
| `standards_creator` | Читает стандарты мировых брендов из интернета, адаптирует под клиента | ✅ | `standards.md` | research_world_brands, adapt_to_client |
| `standards_editor`  | Обновляет стандарты при новых данных | ✅ | `standards.md` | update_standards |
| `advisor`           | Поддержка решений для decision-maker | — | `decisions.md` | decision_options |
| `employee_assistant`| Псевдо-GPT чат для сотрудников (читает `standards.md`) | — | — | answer_about_standards |

`pipeline.txt`: `standards_creator → standards_editor → advisor`
(`employee_assistant` — только чат, вне пайплайна).

---

## 4. Как запустить

```bash
# 1. Зависимости
pip3 install -r requirements.txt

# 2. Ключ API — ТОЛЬКО через переменную окружения, НЕ в файлах!
export ANTHROPIC_API_KEY=sk-ant-...

# 3a. API-сервер (для фронта на Lovable)
python3 -m uvicorn composer.api.app:app --port 8000
#     → Swagger/тест: http://localhost:8000/docs

# 3b. ИЛИ терминал (для разработки/проверки без фронта)
python3 cli.py agents                 # список агентов
python3 cli.py run "создать стандарты обслуживания на основе Starbucks"
python3 cli.py chat employee_assistant
```

### Конфиг (env-переменные, см. `composer/config.py`)

| Переменная | Дефолт | Назначение |
|-----------|--------|------------|
| `ANTHROPIC_API_KEY` | — | ключ к модели (обязателен) |
| `COMPOSER_MODEL` | `claude-sonnet-4-5` | модель |
| `COMPOSER_MAX_TOKENS` | `4096` | макс. токенов в ответе |
| `COMPOSER_MAX_STEPS` | `20` | макс. шагов цикла агента |

> **Python 3.9-совместимость:** в коде НЕ используем синтаксис 3.10+ (`str | None`,
> `list[str]`). Только `typing.Optional/List/Dict`.

---

## 5. API-контракт (для фронтенда Lovable)

База: `http://localhost:8000`. CORS открыт (`allow_origins=["*"]`, dev-режим).

| Метод | Путь | Тело / параметры | Ответ |
|-------|------|------------------|-------|
| GET  | `/api/health` | — | `{"status":"ok"}` |
| GET  | `/api/agents` | — | список карточек: `[{name, description, skills, web, output}]` |
| POST | `/api/agents` | `{name, role, skills?, knowledge?, web?, output?}` | карточка созданного агента |
| GET  | `/api/pipeline` | — | `{"order": [...]}` |
| PUT  | `/api/pipeline` | `{order: [...]}` | `{"order": [...]}` |
| POST | `/api/run` | `{goal: str}` | `{"run_id": "..."}` (запуск в фоне) |
| GET  | `/api/run/{run_id}` | — | `{status, events, results, error}` — **поллить** до `status="done"` |
| POST | `/api/chat` | `{agent, message, session_id?}` | `{session_id, reply, events}` |
| GET  | `/api/files` | — | `{"files": [...]}` (содержимое `workspace/`) |
| GET  | `/api/files/{name}` | — | `{name, content}` |

**Паттерн запуска пайплайна:** `POST /api/run` → получаешь `run_id` →
поллишь `GET /api/run/{run_id}`, пока `status` не станет `done` (или `error`).
В `events` — лог в реальном времени, в `results.files` — готовые документы.

**Хранилища:** `RUNS` и `SESSIONS` — пока **в памяти процесса** (MVP). Для прода — БД.
Стриминг сейчас через поллинг; апгрейд до SSE — возможное улучшение.

---

## 6. Безопасность (ВАЖНО для агентов и людей)

- **Никогда не коммить секреты.** Файл `token`, `.env`, `*.key` — в `.gitignore`.
- **Ключ API — только через `export ANTHROPIC_API_KEY=...`**, не в файлах репозитория.
- `workspace/`, `memory.json`, `memory_chat_*.json` — рантайм-данные, тоже в `.gitignore`.

---

## 7. Состояние и что делать дальше

**Сделано:** чистая архитектура (4 шва), событийный движок, агенты-папки,
детерминированное сохранение результатов, реальный веб-поиск (`ddgs` с фолбэком по
бэкендам), FastAPI-бэкенд с документированным контрактом.

**Дальше:**
- Фронт на Lovable против этого API.
- (Опц.) SSE-стриминг вместо поллинга.
- (Опц.) Замена in-memory `RUNS`/`SESSIONS` на БД.
- Расширение библиотеки агентов (просто добавляя папки в `agents/`).
