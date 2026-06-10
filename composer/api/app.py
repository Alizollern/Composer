"""
Composer AI — REST API для фронтенда (Lovable).

Запуск:
    export ANTHROPIC_API_KEY=sk-ant-...
    uvicorn composer.api.app:app --reload --port 8000
    Документация и тест: http://localhost:8000/docs

Эндпоинты:
  GET  /api/health                  — проверка
  GET  /api/agents                  — список агентов (карточки)
  POST /api/agents                  — создать/обновить агента (harness)
  GET  /api/pipeline                — текущий порядок пайплайна
  PUT  /api/pipeline                — задать порядок
  POST /api/run                     — запустить пайплайн (фоном) -> run_id
  GET  /api/run/{run_id}            — статус + события + результаты (поллинг)
  POST /api/chat                    — диалог с агентом (псевдо-GPT)
  GET  /api/files                   — список файлов workspace
  GET  /api/files/{name}            — содержимое файла workspace
"""

import uuid
import threading
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from composer.config import WORKSPACE
from composer.engine.providers import ClaudeProvider
from composer.engine.memory import JSONMemory
from composer.engine.loop import run_agent
from composer.agents.loader import (
    discover_agents, describe_agent, load_agent, create_agent,
)
from composer.orchestration.orchestrator import (
    orchestrate, load_pipeline, set_pipeline,
)

app = FastAPI(title="Composer AI API", version="0.1.0")

# Фронт на Lovable живёт на другом домене — открываем CORS (для dev).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Хранилища в памяти (для MVP; позже — БД).
RUNS = {}        # run_id -> {status, events, results, error}
SESSIONS = {}    # session_id -> history (список сообщений для чата)


# ---------- Модели запросов ----------
class RunRequest(BaseModel):
    goal: str


class ChatRequest(BaseModel):
    agent: str
    message: str
    session_id: Optional[str] = None


class PipelineRequest(BaseModel):
    order: List[str]


class AgentRequest(BaseModel):
    name: str
    role: str
    skills: Optional[Dict[str, str]] = None
    knowledge: Optional[Dict[str, str]] = None
    web: bool = False
    output: Optional[str] = None


# ---------- Базовое ----------
@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------- Агенты ----------
@app.get("/api/agents")
def list_agents():
    return [describe_agent(n) for n in discover_agents()]


@app.post("/api/agents")
def upsert_agent(req: AgentRequest):
    return create_agent(req.name, req.role, req.skills, req.knowledge, req.web, req.output)


# ---------- Пайплайн ----------
@app.get("/api/pipeline")
def get_pipeline():
    return {"order": load_pipeline()}


@app.put("/api/pipeline")
def put_pipeline(req: PipelineRequest):
    return {"order": set_pipeline(req.order)}


# ---------- Запуск пайплайна (фоном + поллинг) ----------
def _run_pipeline(run_id, goal):
    run = RUNS[run_id]
    try:
        results = orchestrate(goal, on_event=lambda e: run["events"].append(e))
        run["results"] = results
        run["status"] = "done"
    except Exception as e:
        run["status"] = "error"
        run["error"] = str(e)


@app.post("/api/run")
def start_run(req: RunRequest):
    run_id = uuid.uuid4().hex[:12]
    RUNS[run_id] = {"status": "running", "events": [], "results": None, "error": None}
    threading.Thread(target=_run_pipeline, args=(run_id, req.goal), daemon=True).start()
    return {"run_id": run_id}


@app.get("/api/run/{run_id}")
def get_run(run_id):
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "run не найден")
    return run


# ---------- Чат с агентом ----------
@app.post("/api/chat")
def chat(req: ChatRequest):
    if req.agent not in discover_agents():
        raise HTTPException(404, f"Нет агента {req.agent}")
    session_id = req.session_id or uuid.uuid4().hex[:12]
    history = SESSIONS.setdefault(session_id, [])

    agent = load_agent(req.agent)
    memory = JSONMemory(WORKSPACE.parent / f"memory_chat_{req.agent}.json")
    events = []
    reply = run_agent(req.message, ClaudeProvider(), agent["tools"], memory,
                      system=agent["system"], history=history,
                      on_event=lambda e: events.append(e))
    return {"session_id": session_id, "reply": reply, "events": events}


# ---------- Файлы workspace ----------
@app.get("/api/files")
def list_workspace_files():
    return {"files": [str(f.relative_to(WORKSPACE))
                      for f in WORKSPACE.rglob("*") if f.is_file()]}


@app.get("/api/files/{name:path}")
def get_workspace_file(name):
    p = (WORKSPACE / name).resolve()
    if not str(p).startswith(str(WORKSPACE.resolve())) or not p.exists():
        raise HTTPException(404, "Файл не найден")
    return {"name": name, "content": p.read_text()}
