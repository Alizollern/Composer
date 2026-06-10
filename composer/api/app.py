"""
Composer AI — REST API для фронтенда (Lovable).

Запуск:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 -m uvicorn composer.api.app:app --reload --port 8000
    Документация и тест: http://localhost:8000/docs

Платформа («harness as infrastructure»):
  - агенты = папки (создаются через API, без правок кода);
  - интеграции = плагины-инструменты (реестр);
  - оркестрация = агент-оркестратор делегирует суб-агентам, в т.ч. ПАРАЛЛЕЛЬНО;
  - прогоны фоновые: статус поллингом или поток событий через SSE.

Эндпоинты:
  GET  /api/health
  GET  /api/agents                  — список карточек агентов
  POST /api/agents                  — создать/обновить агента (harness)
  GET  /api/agents/{name}           — карточка одного агента
  POST /api/agents/{name}/run       — запустить одного агента (фоном) -> run_id
  GET  /api/integrations            — доступные интеграции (плагины)
  GET  /api/pipeline                — линейный порядок (legacy режим)
  PUT  /api/pipeline                — задать линейный порядок
  POST /api/run                     — запустить оркестрацию (фоном) -> run_id
                                      body: {goal, mode: "dynamic"|"pipeline", orchestrator?}
  GET  /api/run/{run_id}            — статус + события + результаты (поллинг)
  GET  /api/run/{run_id}/stream     — поток событий (SSE, реальное время)
  GET  /api/runs                    — история прогонов
  POST /api/chat                    — диалог с агентом (псевдо-GPT)
  GET  /api/files                   — список файлов workspace
  GET  /api/files/{name}            — содержимое файла workspace
"""

import json
import threading
import uuid
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from composer.config import WORKSPACE, ROOT
from composer.engine.providers import ClaudeProvider
from composer.engine.memory import JSONMemory
from composer.engine.loop import run_agent
from composer.engine.runs import create_run, get_run, list_runs, RUNS
from composer.agents.loader import (
    discover_agents, describe_agent, load_agent, create_agent,
)
from composer.tools.base import list_integrations
from composer.orchestration.orchestrator import (
    orchestrate, load_pipeline, set_pipeline,
)
from composer.orchestration.planner import orchestrate_dynamic
from composer.orchestration.runner import run_agent_by_name
from composer import companies

app = FastAPI(title="Composer AI API", version="0.2.0")

# Фронт на Lovable живёт на другом домене — открываем CORS (для dev).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

SESSIONS = {}  # session_id -> история чата


# ---------- Модели запросов ----------
class RunRequest(BaseModel):
    goal: str
    mode: str = "dynamic"            # "dynamic" (оркестратор-агент) | "pipeline" (линейно)
    orchestrator: Optional[str] = None
    company: Optional[str] = None    # slug компании: прогон скоупится на её папку


class AgentRunRequest(BaseModel):
    task: str
    company: Optional[str] = None


class CompanyRequest(BaseModel):
    name: str
    profile: Optional[str] = None


class ProfileRequest(BaseModel):
    content: str


class ChatRequest(BaseModel):
    agent: str
    message: str
    session_id: Optional[str] = None


class PipelineRequest(BaseModel):
    order: List[str]


class AgentRequest(BaseModel):
    name: str
    role: str
    description: Optional[str] = None
    skills: Optional[Dict[str, str]] = None
    knowledge: Optional[Dict[str, str]] = None
    web: bool = False
    integrations: Optional[List[str]] = None
    subagents: Optional[List[str]] = None
    model: Optional[str] = None
    parallel: Optional[bool] = None
    output: Optional[str] = None
    knowledge_refs: Optional[List[str]] = None


# ---------- Базовое ----------
@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------- Агенты ----------
@app.get("/api/agents")
def list_agents():
    return [describe_agent(n) for n in discover_agents()]


@app.get("/api/agents/{name}")
def get_agent(name: str):
    if name not in discover_agents():
        raise HTTPException(404, f"Нет агента {name}")
    return describe_agent(name)


@app.post("/api/agents")
def upsert_agent(req: AgentRequest):
    return create_agent(
        req.name, req.role, skills=req.skills, knowledge=req.knowledge,
        web=req.web, output=req.output, integrations=req.integrations,
        subagents=req.subagents, model=req.model, parallel=req.parallel,
        description=req.description, knowledge_refs=req.knowledge_refs,
    )


@app.post("/api/agents/{name}/run")
def run_single_agent(name: str, req: AgentRunRequest):
    if name not in discover_agents():
        raise HTTPException(404, f"Нет агента {name}")
    run = create_run("agent", req.task)

    def work():
        try:
            res = run_agent_by_name(name, req.task, on_event=run.emit,
                                    company=req.company)
            run.finish(results=res)
        except Exception as e:
            run.finish(error=str(e))

    threading.Thread(target=work, daemon=True).start()
    return {"run_id": run.id}


# ---------- Интеграции ----------
@app.get("/api/integrations")
def integrations():
    return list_integrations()


# ---------- Компании (мульти-тенант) ----------
@app.get("/api/companies")
def get_companies():
    return {"companies": companies.list_companies()}


@app.post("/api/companies")
def create_company(req: CompanyRequest):
    return companies.create_company(req.name, profile=req.profile or "")


@app.get("/api/companies/{slug}")
def company_detail(slug: str):
    c = companies.get_company(slug)
    if not c:
        raise HTTPException(404, f"Нет компании {slug}")
    return c


@app.put("/api/companies/{slug}/profile")
def company_profile(slug: str, req: ProfileRequest):
    c = companies.update_profile(slug, req.content)
    if not c:
        raise HTTPException(404, f"Нет компании {slug}")
    return c


@app.get("/api/companies/{slug}/files/{name:path}")
def company_file(slug: str, name: str):
    content = companies.read_file(slug, name)
    if content is None:
        raise HTTPException(404, "Файл не найден")
    return {"name": name, "content": content}


# ---------- Пайплайн (legacy линейный режим) ----------
@app.get("/api/pipeline")
def get_pipeline():
    return {"order": load_pipeline()}


@app.put("/api/pipeline")
def put_pipeline(req: PipelineRequest):
    return {"order": set_pipeline(req.order)}


# ---------- Запуск оркестрации (фоном) ----------
@app.post("/api/run")
def start_run(req: RunRequest):
    run = create_run(req.mode, req.goal)

    def work():
        try:
            if req.mode == "pipeline":
                res = orchestrate(req.goal, on_event=run.emit)
            else:
                res = orchestrate_dynamic(
                    req.goal, orchestrator=req.orchestrator,
                    on_event=run.emit, company=req.company)
            run.finish(results=res)
        except Exception as e:
            run.finish(error=str(e))

    threading.Thread(target=work, daemon=True).start()
    return {"run_id": run.id}


@app.get("/api/run/{run_id}")
def run_status(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, "run не найден")
    return run


@app.get("/api/run/{run_id}/stream")
def run_stream(run_id: str):
    run = RUNS.get(run_id)
    if not run:
        # уже завершён и выгружен — отдадим финальный снапшот одним событием
        snap = get_run(run_id)
        if not snap:
            raise HTTPException(404, "run не найден")

        def once():
            yield _sse({"type": "snapshot", **snap})
            yield _sse({"type": "end", "status": snap.get("status")})
        return StreamingResponse(once(), media_type="text/event-stream")

    def gen():
        q = run.subscribe()
        while True:
            ev = q.get()
            if ev.get("type") == "_end":
                yield _sse({"type": "end", "status": run.status})
                break
            yield _sse(ev)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/runs")
def runs_history():
    return {"runs": list_runs()}


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
    reply = run_agent(req.message, ClaudeProvider(model=agent.get("model")),
                      agent["tools"], memory, system=agent["system"],
                      history=history, on_event=lambda e: events.append(e))
    return {"session_id": session_id, "reply": reply, "events": events}


# ---------- Файлы workspace ----------
@app.get("/api/files")
def list_workspace_files():
    return {"files": [str(f.relative_to(WORKSPACE))
                      for f in WORKSPACE.rglob("*")
                      if f.is_file() and ".runs" not in f.parts]}


@app.get("/api/files/{name:path}")
def get_workspace_file(name: str):
    p = (WORKSPACE / name).resolve()
    if not str(p).startswith(str(WORKSPACE.resolve())) or not p.exists():
        raise HTTPException(404, "Файл не найден")
    return {"name": name, "content": p.read_text()}


# ---------- helpers ----------
def _sse(obj):
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


# ---------- Фронтенд (Evergreen, React+Vite) ----------
# Регистрируется ПОСЛЕ всех /api-роутов, чтобы SPA-catch-all их не перехватывал.
# Собранный фронт лежит в frontend/dist (npm run build). Если сборки ещё нет —
# подсказываем, как собрать.
WEB_DIST = ROOT / "frontend" / "dist"

if (WEB_DIST / "index.html").exists():
    _assets = WEB_DIST / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # /api/* сюда не попадают (роуты выше уже их обслужили); но если кто-то
        # дёрнул несуществующий /api — отдаём 404, а не HTML.
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        candidate = (WEB_DIST / full_path).resolve()
        if full_path and str(candidate).startswith(str(WEB_DIST.resolve())) and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(WEB_DIST / "index.html"))
else:
    @app.get("/")
    def need_build():
        return {
            "status": "frontend не собран",
            "hint": "cd frontend && npm install && npm run build",
        }
