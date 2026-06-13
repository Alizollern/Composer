#!/usr/bin/env python3
"""
Сквозной офлайн-тест Evergreen «как тестировщик»: проходит весь путь компании
ЧЕРЕЗ тот же HTTP-API, что зовёт фронтенд, и печатает читаемый отчёт.

Зачем: убедиться, что бэкенд реально работает end-to-end, БЕЗ живого ключа LLM
и БЕЗ Postgres. Всё детерминированно:
  * БД        — SQLite в памяти;
  * эмбеддер  — FakeEmbedder (офлайн, без сети);
  * LLM       — подменён фейком (brain.complete), чтобы проверить ПРОВОДКУ
                (гейты, ссылки на источники, генерацию/оценку теста), не тратя ключ.

Параллельно ведётся журнал «мыслей» агента (product/agent_log) в
var/logs/demo_agent.jsonl — в конце печатаем его хвост.

Запуск:  python3 scripts/test_flow.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# --- Окружение ДО импорта продуктовых модулей: форсим офлайн-режим. ---
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["EVERGREEN_EMBEDDER"] = "fake"          # эмбеддер без сети
os.environ["EVERGREEN_EMBEDDING_DIM"] = "256"      # размерность FakeEmbedder
os.environ["EVERGREEN_STORAGE_BACKEND"] = "local"
os.environ["EVERGREEN_STORAGE_DIR"] = tempfile.mkdtemp(prefix="evergreen-demo-")
os.environ.setdefault("EVERGREEN_JWT_SECRET", "demo-secret")
os.environ["EVERGREEN_AGENT_LOG"] = str(ROOT / "var" / "logs" / "demo_agent.jsonl")

from fastapi.testclient import TestClient                      # noqa: E402
from sqlalchemy import create_engine                           # noqa: E402
from sqlalchemy.pool import StaticPool                         # noqa: E402

from product.db.session import make_session_factory, init_db   # noqa: E402
from product.auth.deps import get_db                           # noqa: E402
from product.api.app import create_app                         # noqa: E402
from product import brain                                      # noqa: E402
from product.modules import chat as chat_module               # noqa: E402


# ----------------------------------------------------------------------------
# Фейковый LLM: заменяет brain.complete. НИЧЕГО не зовёт по сети.
#   * генерация теста (M3) — отдаём валидный JSON-массив вопросов;
#   * чат (M2) с фрагментами — отвечаем «по документу» и ссылаемся на источник;
#   * иначе — маркер отказа.
# ----------------------------------------------------------------------------
_FAKE_QUIZ_JSON = (
    '[{"question": "За сколько дней предупреждать о заморозке абонемента?", '
    '"options": ["За 1 день", "За 3 дня", "За неделю", "Не нужно"], '
    '"correct_index": 1, '
    '"source_quote": "Заморозку оформляем по заявлению минимум за 3 дня."}]'
)


def _fake_answer(system: str, user: str) -> str:
    if "проверочный тест" in system:
        return _FAKE_QUIZ_JSON
    if "Фрагмент 1" in user:
        # Достаём название документа из контекста, чтобы ссылка была настоящей.
        title = "стандарт"
        for line in user.splitlines():
            if "Документ:" in line:
                title = line.split("«")[-1].split("»")[0] or title
                break
        return (f"По стандарту компании заморозку абонемента оформляем по "
                f"заявлению минимум за 3 дня. Источник: «{title}».")
    return chat_module.REFUSAL_MARKER


class FakeProvider:
    """Подменяет LLM-провайдера: имеет тот же .call(), что и Claude/Gemini.

    Так демо проходит через НАСТОЯЩИЙ brain.complete() — а значит, в журнал
    агента попадают и записи llm.complete (что спросили у модели и что она
    «ответила»), ровно как в реальной работе с ключом."""

    def call(self, system, messages, tools):
        user = messages[-1]["content"] if messages else ""
        return {"text": _fake_answer(system, user), "tool_calls": [],
                "stop_reason": "end_turn", "raw_content": []}


# ----------------------------------------------------------------------------
# Маленький помощник для печати шагов.
# ----------------------------------------------------------------------------
_STEP = 0


def step(title: str) -> None:
    global _STEP
    _STEP += 1
    print(f"\n{'─' * 70}\n  ШАГ {_STEP}. {title}\n{'─' * 70}")


def ok(msg: str) -> None:
    print(f"   ✅ {msg}")


def info(msg: str) -> None:
    print(f"   • {msg}")


def fail(msg: str) -> None:
    print(f"   ❌ {msg}")
    raise SystemExit(1)


# ----------------------------------------------------------------------------
# Сборка приложения с тестовой БД.
# ----------------------------------------------------------------------------
def build_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool, future=True)
    init_db(engine)
    factory = make_session_factory(engine)

    app = create_app()

    def _override_get_db():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db
    # Подменяем ПРОВАЙДЕРА (а не сам complete) — тогда работает настоящий
    # brain.complete() с журналированием, но без сети и без ключа.
    brain.get_provider = lambda *a, **k: FakeProvider()
    return TestClient(app)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    # Чистим журнал прошлого прогона, чтобы хвост показывал именно этот запуск.
    log_path = Path(os.environ["EVERGREEN_AGENT_LOG"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        log_path.unlink()

    print("=" * 70)
    print("  EVERGREEN — СКВОЗНОЙ ОФЛАЙН-ТЕСТ (как тестировщик)")
    print("  БД: SQLite · Эмбеддер: Fake · LLM: фейк (ключ не нужен)")
    print("=" * 70)

    c = build_client()

    # 1. Здоровье сервиса
    step("Проверяем, что API живой (/api/health)")
    r = c.get("/api/health")
    if r.status_code == 200 and r.json().get("status") == "ok":
        ok("API отвечает: " + str(r.json()))
    else:
        fail(f"health вернул {r.status_code}: {r.text}")

    # 2. Регистрация компании (owner)
    step("Регистрируем компанию и владельца (как форма «Создать компанию»)")
    r = c.post("/api/auth/register-company", json={
        "company_name": "Bronx Fitness",
        "slug": "bronx-fitness",
        "owner_email": "owner@bronx.kz",
        "owner_password": "secret123",
        "owner_name": "Ляззат Иргалиева",
    })
    if r.status_code != 200:
        fail(f"Регистрация не удалась {r.status_code}: {r.text}")
    owner = r.json()
    owner_token = owner["access_token"]
    ok(f"Компания создана. Роль владельца: {owner['role']}, company_id={owner['company_id'][:8]}…")

    # 3. Заводим сотрудника
    step("Владелец создаёт сотрудника (администратора зала)")
    r = c.post("/api/users", headers=auth(owner_token), json={
        "email": "admin@bronx.kz", "password": "secret123",
        "role": "employee", "full_name": "Айгерим",
    })
    if r.status_code != 201:
        fail(f"Создание сотрудника не удалось {r.status_code}: {r.text}")
    employee = r.json()
    ok(f"Сотрудник создан: {employee['email']} (роль {employee['role']})")

    # 4. Загружаем два стандарта (опубликованные)
    step("Владелец загружает 2 стандарта в Базу знаний")
    docs = []
    for title, content, category in [
        ("Стандарт администратора: заморозка абонемента",
         "Заморозку абонемента оформляем по заявлению клиента минимум за 3 дня. "
         "Минимальный срок заморозки — 7 дней, максимальный — 30 дней в год. "
         "Замороженные дни продлевают срок действия абонемента.",
         "Администраторам"),
        ("Стандарт уборки тренажёрного зала",
         "Влажную уборку зала проводим дважды в день: утром до открытия и вечером "
         "после закрытия. Тренажёры протираем антисептиком каждые два часа.",
         "Персоналу"),
    ]:
        r = c.post("/api/documents", headers=auth(owner_token), json={
            "title": title, "content": content, "category": category, "publish": True,
        })
        if r.status_code != 201:
            fail(f"Загрузка документа не удалась {r.status_code}: {r.text}")
        docs.append(r.json())
        ok(f"Загружен и опубликован: «{title}» (status={r.json()['status']})")

    # 5. Вход сотрудника
    step("Сотрудник входит в систему (форма «Войти»)")
    r = c.post("/api/auth/login", json={
        "slug": "bronx-fitness", "email": "admin@bronx.kz", "password": "secret123",
    })
    if r.status_code != 200:
        fail(f"Вход сотрудника не удался {r.status_code}: {r.text}")
    emp_token = r.json()["access_token"]
    ok("Сотрудник вошёл, получил токен")

    # 6. Сотрудник видит опубликованные стандарты
    step("Сотрудник открывает Базу знаний (видит опубликованное)")
    r = c.get("/api/documents", headers=auth(emp_token), params={"status_filter": "published"})
    visible = r.json()
    ok(f"Сотруднику видно документов: {len(visible)}")
    for d in visible:
        info(f"«{d['title']}»")

    # 7. Чат: вопрос, на который ЕСТЬ ответ в базе
    step("Сотрудник спрашивает бота то, что ЕСТЬ в стандартах")
    r = c.post("/api/chat", headers=auth(emp_token),
               json={"question": "За сколько дней оформлять заморозку абонемента?"})
    a = r.json()
    if a["refused"]:
        fail("Бот отказал, хотя ответ есть в базе — проверь FakeEmbedder/порог")
    ok("Бот ответил по документу:")
    print(f"      «{a['answer']}»")
    info("Источники: " + ", ".join(s["document_title"] for s in a["sources"]))
    info(f"Уверенность (косинус): {a['best_score']:.3f}")

    # 8. Чат: вопрос, ответа на который НЕТ → честный отказ + лог пробела
    step("Сотрудник спрашивает то, чего НЕТ в стандартах (проверяем честность)")
    r = c.post("/api/chat", headers=auth(emp_token),
               json={"question": "Какая корпоративная скидка на протеиновые коктейли?"})
    a = r.json()
    if not a["refused"]:
        fail("Бот выдумал ответ — строгий RAG нарушен!")
    ok("Бот честно отказался (ничего не выдумал):")
    print(f"      «{a['answer']}»")

    # 9. Владелец смотрит «карту пробелов»
    step("Владелец открывает «Карту пробелов» (вопросы без ответа)")
    r = c.get("/api/gaps", headers=auth(owner_token))
    gaps = r.json()
    ok(f"Зафиксировано пробелов: {len(gaps)}")
    for g in gaps:
        info(f"«{g['question']}» (близость {g['best_score']:.3f}, решён={g['resolved']})")

    # 10. Генерация теста по стандарту + автопроверка
    step("Владелец генерирует тест по стандарту, сотрудник его проходит")
    doc_id = docs[0]["id"]
    r = c.post(f"/api/documents/{doc_id}/quiz", headers=auth(owner_token),
               json={"num_questions": 1})
    if r.status_code != 200:
        fail(f"Генерация теста не удалась {r.status_code}: {r.text}")
    quiz = r.json()["questions"]
    ok(f"Сгенерирован тест из {len(quiz)} вопрос(ов):")
    for q in quiz:
        info(f"Q: {q['question']}  (варианты: {q['options']})")
    # Сотрудник отвечает правильно (берём correct_index)
    answers = [q["correct_index"] for q in quiz]
    r = c.post("/api/quiz/grade", headers=auth(emp_token),
               json={"quiz": quiz, "answers": answers})
    grade = r.json()
    ok(f"Результат: {grade['correct']}/{grade['total']} (сдал={grade['passed']})")

    # 11. Трек онбординга: создать → шаг → опубликовать → зачислить → пройти
    step("Владелец собирает трек онбординга и зачисляет сотрудника")
    r = c.post("/api/tracks", headers=auth(owner_token),
               json={"title": "Онбординг администратора", "description": "Базовый курс"})
    track = r.json()
    ok(f"Трек создан: «{track['title']}» (status={track['status']})")
    r = c.post(f"/api/tracks/{track['id']}/steps", headers=auth(owner_token),
               json={"document_id": doc_id, "title": "Изучить заморозку",
                     "require_quiz": True, "pass_score": 0.8, "num_questions": 1})
    step_obj = r.json()
    ok(f"Добавлен шаг: «{step_obj['title']}»")
    c.post(f"/api/tracks/{track['id']}/status", headers=auth(owner_token),
           json={"status": "published"})
    ok("Трек опубликован")
    r = c.post(f"/api/tracks/{track['id']}/enroll", headers=auth(owner_token),
               json={"user_id": employee["id"]})
    enrollment = r.json()
    ok(f"Сотрудник зачислен (enrollment status={enrollment['status']})")

    # 12. Сотрудник проходит шаг трека (с тестом)
    step("Сотрудник проходит шаг трека (отвечает на тест)")
    r = c.get("/api/my/enrollments", headers=auth(emp_token))
    my = r.json()[0]
    st = my["steps"][0]
    # Генерируем тест шага через документ и отвечаем верно.
    r = c.post(f"/api/documents/{doc_id}/quiz", headers=auth(owner_token),
               json={"num_questions": 1})
    step_quiz = r.json()["questions"]
    r = c.post(
        f"/api/enrollments/{my['enrollment_id']}/steps/{st['id']}/submit",
        headers=auth(emp_token),
        json={"quiz": step_quiz, "answers": [q["correct_index"] for q in step_quiz]})
    res = r.json()
    ok(f"Шаг сдан: статус={res['step_status']}, счёт={res['score']}, "
       f"трек={res['enrollment_status']}")

    # 13. Владелец смотрит прогресс по треку
    step("Владелец смотрит прогресс команды по треку")
    r = c.get(f"/api/tracks/{track['id']}/progress", headers=auth(owner_token))
    for row in r.json():
        info(f"Сотрудник {row['user_id'][:8]}…: {row['passed_steps']}/{row['total_steps']} "
             f"шагов, статус={row['status']}")

    # --- Хвост журнала «мыслей» агента ---
    print(f"\n{'=' * 70}\n  ЖУРНАЛ «МЫСЛЕЙ» АГЕНТА (var/logs/demo_agent.jsonl)\n{'=' * 70}")
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8").splitlines()
        info(f"Всего записей: {len(lines)} (показываю все)")
        import json as _json
        for ln in lines:
            rec = _json.loads(ln)
            kind = rec.get("kind")
            if kind == "chat.retrieval":
                cands = ", ".join(f"{x['title']}:{x['score']}" for x in rec.get("candidates", []))
                print(f"   [{rec['ts']}] 🔎 ретривал → лучшее {rec['best_score']} "
                      f"(порог {rec['min_score']}) | {cands}")
            elif kind == "chat.decision":
                print(f"   [{rec['ts']}] 🧭 решение={rec['decision']} (гейт {rec['gate']})")
            elif kind == "llm.complete":
                out = (rec.get("output") or "")[:80].replace("\n", " ")
                print(f"   [{rec['ts']}] 🤖 LLM {rec.get('operation')} "
                      f"({rec.get('elapsed_ms')}мс) → «{out}…»")
            else:
                print(f"   [{rec['ts']}] {kind}: {rec}")
    else:
        fail("Журнал агента не создан")

    print(f"\n{'=' * 70}\n  ✅ ВСЁ ПРОШЛО. Бэкенд работает end-to-end (офлайн).\n{'=' * 70}")


if __name__ == "__main__":
    main()
