"""
Хранилище прогонов (runs) — статус, события, результаты.

Зачем: API запускает оркестрацию/агента в фоне и отдаёт run_id; фронт либо
поллит статус, либо подписывается на поток событий (SSE). Прогоны
персистятся на диск (workspace/.runs/), чтобы переживать рестарт.

Потокобезопасно: события эмитятся из нескольких потоков (параллельные агенты),
поэтому добавление в список и рассылка подписчикам защищены локом.
"""

import json
import time
import uuid
import queue
import threading

from composer.config import RUNS_DIR

_END = {"type": "_end"}
RUNS = {}  # run_id -> Run (живые, в памяти)


class Run:
    def __init__(self, kind, goal):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind            # "dynamic" | "pipeline" | "agent" | "chat"
        self.goal = goal
        self.status = "running"     # running | done | error
        self.events = []
        self.results = None
        self.error = None
        self.created = time.time()
        self._subs = []             # очереди подписчиков (SSE)
        self._lock = threading.Lock()

    def emit(self, event):
        with self._lock:
            self.events.append(event)
            subs = list(self._subs)
        for q in subs:
            q.put(event)

    def subscribe(self):
        q = queue.Queue()
        with self._lock:
            for e in self.events:   # сначала проигрываем уже накопленное
                q.put(e)
            if self.status != "running":
                q.put(_END)
            else:
                self._subs.append(q)
        return q

    def finish(self, results=None, error=None):
        with self._lock:
            self.status = "error" if error else "done"
            self.results = results
            self.error = error
            subs = list(self._subs)
        for q in subs:
            q.put(_END)
        self.persist()

    def snapshot(self):
        return {"id": self.id, "kind": self.kind, "goal": self.goal,
                "status": self.status, "events": self.events,
                "results": self.results, "error": self.error,
                "created": self.created}

    def persist(self):
        try:
            (RUNS_DIR / f"{self.id}.json").write_text(
                json.dumps(self.snapshot(), ensure_ascii=False, indent=2))
        except Exception:
            pass


def create_run(kind, goal):
    r = Run(kind, goal)
    RUNS[r.id] = r
    return r


def get_run(run_id):
    """Живой Run (snapshot) или загруженный с диска (dict). None если нет."""
    if run_id in RUNS:
        return RUNS[run_id].snapshot()
    p = RUNS_DIR / f"{run_id}.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def list_runs(limit=50):
    seen = {}
    for r in RUNS.values():
        s = r.snapshot()
        seen[r.id] = {k: s[k] for k in ("id", "kind", "goal", "status", "created")}
    for f in RUNS_DIR.glob("*.json"):
        if f.stem in seen:
            continue
        try:
            s = json.loads(f.read_text())
            seen[s["id"]] = {k: s.get(k) for k in
                             ("id", "kind", "goal", "status", "created")}
        except Exception:
            continue
    runs = sorted(seen.values(), key=lambda x: x.get("created") or 0, reverse=True)
    return runs[:limit]
