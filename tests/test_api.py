"""Тесты HTTP-API: регистрация/вход, RBAC, изоляция тенантов, чат через API."""

import json


def _register(client, slug="acme", email="owner@acme.io", pw="secret1"):
    r = client.post("/api/auth/register-company", json={
        "company_name": slug.title(), "slug": slug,
        "owner_email": email, "owner_password": pw, "owner_name": "Босс"})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_login_me(client):
    tok = _register(client)["access_token"]
    me = client.get("/api/auth/me", headers=_auth(tok))
    assert me.status_code == 200
    assert me.json()["role"] == "owner"


def test_no_token_is_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_owner_creates_employee_and_employee_cannot_ingest(client):
    owner = _register(client)["access_token"]
    # owner заводит сотрудника
    r = client.post("/api/users", headers=_auth(owner), json={
        "email": "worker@acme.io", "password": "secret1", "role": "employee"})
    assert r.status_code == 201, r.text
    # сотрудник логинится
    emp = client.post("/api/auth/login", json={
        "slug": "acme", "email": "worker@acme.io", "password": "secret1"}).json()
    emp_tok = emp["access_token"]
    # сотрудник НЕ может загружать стандарты (нужен manager+)
    r = client.post("/api/documents", headers=_auth(emp_tok), json={
        "title": "X", "content": "текст"})
    assert r.status_code == 403


def test_employee_cannot_create_users(client):
    owner = _register(client)["access_token"]
    client.post("/api/users", headers=_auth(owner), json={
        "email": "w@acme.io", "password": "secret1", "role": "employee"})
    emp = client.post("/api/auth/login", json={
        "slug": "acme", "email": "w@acme.io", "password": "secret1"}).json()["access_token"]
    r = client.post("/api/users", headers=_auth(emp), json={
        "email": "x@acme.io", "password": "secret1", "role": "employee"})
    assert r.status_code == 403


def test_full_flow_ingest_and_chat(client):
    owner = _register(client)["access_token"]
    r = client.post("/api/documents", headers=_auth(owner), json={
        "title": "Стандарт кофе",
        "content": "Эспрессо готовим при температуре 92 градуса.",
        "category": "barista"})
    assert r.status_code == 201, r.text

    # вопрос по базе → ответ с источником
    r = client.post("/api/chat", headers=_auth(owner),
                    json={"question": "при какой температуре эспрессо 92 градуса"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["refused"] is False
    assert body["sources"]

    # вопрос вне базы → отказ, пробел залогирован
    r = client.post("/api/chat", headers=_auth(owner),
                    json={"question": "какой пароль от сейфа в подсобке"})
    assert r.json()["refused"] is True

    gaps = client.get("/api/gaps", headers=_auth(owner)).json()
    assert len(gaps) == 1


def test_quiz_generation_and_grading_over_api(client):
    owner = _register(client)["access_token"]
    doc = client.post("/api/documents", headers=_auth(owner), json={
        "title": "Стандарт кофе",
        "content": "Эспрессо готовим при температуре 92 градуса."}).json()
    # менеджер/owner генерирует тест по документу
    r = client.post(f"/api/documents/{doc['id']}/quiz", headers=_auth(owner),
                    json={"num_questions": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    token = body["quiz_token"]
    quiz = body["questions"]
    assert quiz and len(quiz[0]["options"]) == 4
    # Правильные ответы клиенту НЕ отдаются вместе с вопросами.
    assert "correct_index" not in quiz[0]
    assert "source_quote" not in quiz[0]
    # Верный ответ узнаём только из разбора после проверки (а не из выдачи теста).
    probe = client.post("/api/quiz/grade", headers=_auth(owner),
                        json={"quiz_token": token, "answers": [0]})
    assert probe.status_code == 200
    correct_index = probe.json()["details"][0]["correct_index"]
    # оценивание по серверной копии: верный ответ -> зачёт
    g = client.post("/api/quiz/grade", headers=_auth(owner),
                    json={"quiz_token": token, "answers": [correct_index]})
    assert g.status_code == 200
    assert g.json()["correct"] == 1


def test_quiz_answers_not_leaked_to_client(client):
    # Главная цель фикса: тест уходит в браузер БЕЗ правильных ответов, а оценка
    # считается на сервере по сохранённой копии (по токену).
    owner = _register(client)["access_token"]
    doc = client.post("/api/documents", headers=_auth(owner), json={
        "title": "Стандарт кофе",
        "content": "Эспрессо готовим при температуре 92 градуса."}).json()
    body = client.post(f"/api/documents/{doc['id']}/quiz", headers=_auth(owner),
                       json={"num_questions": 1}).json()
    # Выдача теста: есть токен и вопросы, но НЕТ correct_index/source_quote.
    assert body["quiz_token"]
    for q in body["questions"]:
        assert "correct_index" not in q
        assert "source_quote" not in q
    # Никакой ответ в полезной нагрузке не выдаёт правильный вариант.
    import json as _json
    assert "correct_index" not in _json.dumps(body)
    # Несуществующий токен теста → 404 (нельзя грейдить «свой» произвольный тест).
    bad = client.post("/api/quiz/grade", headers=_auth(owner),
                      json={"quiz_token": "deadbeef", "answers": [0]})
    assert bad.status_code == 404


def test_quiz_token_tenant_isolated(client):
    # Токен теста одной компании нельзя использовать в другой (изоляция тенанта).
    a = _register(client, slug="acme", email="a@a.io")["access_token"]
    b = _register(client, slug="beta", email="b@b.io")["access_token"]
    doc = client.post("/api/documents", headers=_auth(a), json={
        "title": "A", "content": "Эспрессо при 92 градуса."}).json()
    token = client.post(f"/api/documents/{doc['id']}/quiz", headers=_auth(a),
                        json={"num_questions": 1}).json()["quiz_token"]
    # Компания B с чужим токеном — как будто теста нет.
    r = client.post("/api/quiz/grade", headers=_auth(b),
                    json={"quiz_token": token, "answers": [0]})
    assert r.status_code == 404


def test_employee_quiz_scoped_to_audience(client):
    # Сотрудник может собрать тест по стандарту своей аудитории (для обучения),
    # но НЕ по документу, скрытому от него аудиторией (M1.5).
    owner = _register(client)["access_token"]
    open_doc = client.post("/api/documents", headers=_auth(owner), json={
        "title": "Для всех", "content": "Эспрессо при 92 градуса."}).json()
    mgr_doc = client.post("/api/documents", headers=_auth(owner), json={
        "title": "Только управляющим", "content": "Секретный регламент."}).json()
    # Ограничиваем второй документ аудиторией «manager».
    client.post(f"/api/documents/{mgr_doc['id']}/audience", headers=_auth(owner),
                json={"audience_roles": ["manager"]})
    client.post("/api/users", headers=_auth(owner), json={
        "email": "w@acme.io", "password": "secret1", "role": "employee"})
    emp = client.post("/api/auth/login", json={
        "slug": "acme", "email": "w@acme.io", "password": "secret1"}).json()["access_token"]
    # По «своему» документу — тест доступен.
    ok = client.post(f"/api/documents/{open_doc['id']}/quiz", headers=_auth(emp),
                     json={"num_questions": 1})
    assert ok.status_code == 200
    # По скрытому — как будто документа нет.
    hidden = client.post(f"/api/documents/{mgr_doc['id']}/quiz", headers=_auth(emp),
                         json={"num_questions": 1})
    assert hidden.status_code == 404


def test_tenant_isolation_over_api(client):
    a = _register(client, slug="acme", email="a@a.io")["access_token"]
    b = _register(client, slug="beta", email="b@b.io")["access_token"]
    # A создаёт документ
    client.post("/api/documents", headers=_auth(a), json={
        "title": "Секрет A", "content": "Код сейфа компании A: 4321."})
    # B спрашивает — не должен получить ответ из базы A
    r = client.post("/api/chat", headers=_auth(b),
                    json={"question": "код сейфа компании"})
    assert r.json()["refused"] is True
    # B не видит документы A
    docs_b = client.get("/api/documents", headers=_auth(b)).json()
    assert docs_b == []


def test_learning_autobuild_and_full_flow(client):
    """Микро-обучение целиком: авто-сборка курса → правка → публикация →
    назначение → прохождение шага сотрудником → прогресс у руководителя."""
    owner = _register(client)["access_token"]
    # Два опубликованных стандарта.
    ids = []
    for i in (1, 2):
        d = client.post("/api/documents", headers=_auth(owner), json={
            "title": f"Стандарт {i}",
            "content": f"1. Раздел.\n1.1. Пункт {i}."}).json()
        client.post(f"/api/documents/{d['id']}/status", headers=_auth(owner),
                    json={"status": "published"})
        ids.append(d["id"])

    # Авто-сборка курса из всех опубликованных стандартов (черновик).
    tr = client.post("/api/tracks/auto", headers=_auth(owner), json={})
    assert tr.status_code == 201, tr.text
    track = tr.json()
    assert track["status"] == "draft"
    assert len(track["steps"]) == 2

    # Правка: убрать один шаг — остаётся один, ordinal без дыр.
    drop = track["steps"][0]["id"]
    r = client.delete(f"/api/tracks/{track['id']}/steps/{drop}", headers=_auth(owner))
    assert r.status_code == 204
    detail = client.get(f"/api/tracks/{track['id']}", headers=_auth(owner)).json()
    assert len(detail["steps"]) == 1
    assert detail["steps"][0]["ordinal"] == 0

    # Публикация и назначение сотруднику.
    client.post(f"/api/tracks/{track['id']}/status", headers=_auth(owner),
                json={"status": "published"})
    client.post("/api/users", headers=_auth(owner), json={
        "email": "stud@acme.io", "password": "secret1", "role": "employee",
        "full_name": "Студент"})
    users = client.get("/api/users", headers=_auth(owner)).json()
    emp_id = next(u["id"] for u in users if u["email"] == "stud@acme.io")
    en = client.post(f"/api/tracks/{track['id']}/enroll", headers=_auth(owner),
                     json={"user_id": emp_id})
    assert en.status_code == 201

    # Сотрудник проходит шаг.
    emp = client.post("/api/auth/login", json={
        "slug": "acme", "email": "stud@acme.io", "password": "secret1"}).json()["access_token"]
    enr = client.get("/api/my/enrollments", headers=_auth(emp)).json()[0]
    step = enr["steps"][0]
    # Текст стандарта доступен сотруднику (для карточек).
    content = client.get(f"/api/documents/{step['document_id']}/content", headers=_auth(emp))
    assert content.status_code == 200 and content.json()["content"]
    qz = client.post(f"/api/documents/{step['document_id']}/quiz",
                     headers=_auth(emp), json={"num_questions": 1}).json()
    token = qz["quiz_token"]
    # Вопросы приходят без правильных ответов — подсмотреть нельзя.
    assert all("correct_index" not in q for q in qz["questions"])
    # Узнаём верные ответы из разбора (после проверки) и сдаём шаг по токену.
    probe = client.post("/api/quiz/grade", headers=_auth(emp),
                        json={"quiz_token": token, "answers": [0]}).json()
    answers = [d["correct_index"] for d in probe["details"]]
    res = client.post(
        f"/api/enrollments/{enr['enrollment_id']}/steps/{step['id']}/submit",
        headers=_auth(emp), json={"quiz_token": token, "answers": answers}).json()
    assert res["step_status"] == "passed"
    assert res["enrollment_status"] == "completed"

    # Руководитель видит прогресс.
    prog = client.get(f"/api/tracks/{track['id']}/progress", headers=_auth(owner)).json()
    assert prog and prog[0]["passed_steps"] == prog[0]["total_steps"] == 1


def test_autobuild_requires_published_docs(client):
    owner = _register(client)["access_token"]
    # Без опубликованных стандартов — понятная ошибка 400, а не пустой курс.
    r = client.post("/api/tracks/auto", headers=_auth(owner), json={})
    assert r.status_code == 400


# ---- M4: Командный центр (отзывы 2GIS → инсайты) ----

def _publish_doc(client, owner, title, content, category=""):
    r = client.post("/api/documents", headers=_auth(owner), json={
        "title": title, "content": content, "category": category, "publish": True})
    assert r.status_code == 201, r.text
    return r.json()


def test_command_center_reviews_flow(client):
    owner = _register(client)["access_token"]
    _publish_doc(client, owner, "Правила уборки",
                 "Влажная уборка зала дважды в день. Тренажёры протираются каждые 2 часа.")
    _publish_doc(client, owner, "Стандарт обслуживания",
                 "Сотрудник приветствует клиента в течение 30 секунд, вежливо.")

    # Подключаем точку (источник в тестах — FakeReviewSource: 8 отзывов).
    p = client.post("/api/points", headers=_auth(owner),
                    json={"name": "Зал на Абая", "url": "https://2gis.kz/almaty/firm/70000001006012345"})
    assert p.status_code == 201, p.text
    point_id = p.json()["id"]

    # Синхронизация: тянем + сразу разбираем.
    sync = client.post(f"/api/points/{point_id}/sync", headers=_auth(owner)).json()
    assert sync["added"] == 8
    assert sync["analyzed"] == 8

    # Командный центр: пульс, боли, лента.
    cc = client.get("/api/command-center", headers=_auth(owner)).json()
    assert cc["pulse"]["total"] == 8
    assert cc["pulse"]["negative"] >= 1
    assert cc["pulse"]["complaints"] >= 1
    assert cc["pulse"]["positive"] >= 1
    assert cc["problems"], "должны выделиться главные боли"
    assert len(cc["recent"]) == 8
    pt = cc["points"][0]
    assert pt["reviews_count"] == 8
    # Обогащённые поля точки (для сравнения филиалов в «сети»).
    assert pt["positive_count"] >= 1
    assert pt["complaints_count"] >= 1
    assert pt["avg_rating"] > 0

    # Повторная синхронизация не плодит дубли.
    sync2 = client.post(f"/api/points/{point_id}/sync", headers=_auth(owner)).json()
    assert sync2["added"] == 0


def test_network_overview_ranks_points(db, monkeypatch):
    """Сеть из двух филиалов (good/bad) — проблемная точка видна по метрикам."""
    from product import brain
    from product.modules import accounts, reviews as rv
    from product.reviews.source import FakeReviewSource

    # Модель «недоступна» → разбор честно откатывается к оценке (rating).
    def _boom(*a, **k):
        raise RuntimeError("llm offline")
    monkeypatch.setattr(brain, "complete", _boom)

    company, owner = accounts.register_company(
        db, company_name="Net", slug="net",
        owner_email="o@net.io", owner_password="secret1", owner_name="")
    db.commit()

    good = rv.connect_point(db, company.id, name="Good",
                            url="https://2gis.kz/almaty/firm/111")
    bad = rv.connect_point(db, company.id, name="Bad",
                           url="https://2gis.kz/almaty/firm/222")
    db.commit()
    rv.sync_and_analyze(db, company.id, good.id,
                        source=FakeReviewSource(profile="good", prefix="g-"))
    rv.sync_and_analyze(db, company.id, bad.id,
                        source=FakeReviewSource(profile="bad", prefix="b-"))

    cc = rv.command_center(db, company.id)
    pts = {p["name"]: p for p in cc["points"]}
    assert pts["Good"]["reviews_count"] == 8
    assert pts["Bad"]["reviews_count"] == 8
    # Разные профили → проблемная точка хуже по всем метрикам.
    assert pts["Bad"]["complaints_count"] > pts["Good"]["complaints_count"]
    assert pts["Good"]["avg_rating"] > pts["Bad"]["avg_rating"]


def test_connect_point_rejects_bad_url(client):
    owner = _register(client)["access_token"]
    r = client.post("/api/points", headers=_auth(owner),
                    json={"name": "X", "url": "https://example.com/nope"})
    assert r.status_code == 400


def test_employee_cannot_access_command_center(client):
    owner = _register(client)["access_token"]
    client.post("/api/users", headers=_auth(owner), json={
        "email": "w@acme.io", "password": "secret1", "role": "employee"})
    emp = client.post("/api/auth/login", json={
        "slug": "acme", "email": "w@acme.io", "password": "secret1"}).json()["access_token"]
    assert client.get("/api/command-center", headers=_auth(emp)).status_code == 403
    assert client.post("/api/points", headers=_auth(emp),
                       json={"name": "X", "url": "123"}).status_code == 403


class _FinalLLM:
    """Провайдер-заглушка: сразу отдаёт финальный ответ без вызова инструментов."""
    def call(self, system, messages, tools):
        return {"text": "Вывод: сеть работает штатно.", "tool_calls": [],
                "stop_reason": "end_turn",
                "raw_content": [{"type": "text", "text": "Вывод: сеть работает штатно."}]}


def test_advisor_endpoint(client, monkeypatch):
    from product import brain
    monkeypatch.setattr(brain, "get_provider", lambda *a, **k: _FinalLLM())
    owner = _register(client)["access_token"]
    r = client.post("/api/advisor", headers=_auth(owner),
                    json={"question": "Как дела в сети?"})
    assert r.status_code == 200, r.text
    assert "штатно" in r.json()["answer"]


def test_employee_cannot_access_advisor(client):
    owner = _register(client)["access_token"]
    client.post("/api/users", headers=_auth(owner), json={
        "email": "e2@acme.io", "password": "secret1", "role": "employee"})
    emp = client.post("/api/auth/login", json={
        "slug": "acme", "email": "e2@acme.io", "password": "secret1"}).json()["access_token"]
    assert client.post("/api/advisor", headers=_auth(emp),
                       json={"question": "?"}).status_code == 403


class _ToolThenFinalLLM:
    """Провайдер-заглушка: сначала зовёт инструмент, затем отдаёт финал.
    Нужен, чтобы стрим выдал событие tool_call перед ответом."""
    def __init__(self):
        self.i = 0

    def call(self, system, messages, tools):
        self.i += 1
        if self.i == 1:
            cid = "call_network_overview"
            return {"text": "", "stop_reason": "tool_use",
                    "tool_calls": [{"id": cid, "name": "network_overview", "input": {}}],
                    "raw_content": [{"type": "tool_use", "id": cid,
                                     "name": "network_overview", "input": {}}]}
        text = "Вывод: сеть работает штатно."
        return {"text": text, "tool_calls": [], "stop_reason": "end_turn",
                "raw_content": [{"type": "text", "text": text}]}


def test_advisor_stream_emits_thoughts_and_final(client, monkeypatch):
    """SSE-стрим «мыслей»: в потоке есть вызов инструмента и финальный ответ."""
    from product import brain
    monkeypatch.setattr(brain, "get_provider", lambda *a, **k: _ToolThenFinalLLM())
    owner = _register(client)["access_token"]

    events = []
    with client.stream("POST", "/api/advisor/stream", headers=_auth(owner),
                       json={"question": "Как дела в сети?"}) as r:
        assert r.status_code == 200, r.text
        for line in r.iter_lines():
            if not line:
                continue
            text = line if isinstance(line, str) else line.decode()
            if text.startswith("data:"):
                events.append(json.loads(text[5:].strip()))

    types = [e["type"] for e in events]
    assert "tool_call" in types
    finals = [e for e in events if e["type"] == "final"]
    assert finals and "штатно" in finals[0]["answer"]


def test_digest_endpoint_empty(client):
    """Сводка отдаётся даже без отзывов — пустая, без тревог."""
    owner = _register(client)["access_token"]
    r = client.get("/api/digest", headers=_auth(owner))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_data"] is False
    assert body["alerts"] == []
    assert body["summary"]


def test_employee_cannot_access_digest(client):
    owner = _register(client)["access_token"]
    client.post("/api/users", headers=_auth(owner), json={
        "email": "e3@acme.io", "password": "secret1", "role": "employee"})
    emp = client.post("/api/auth/login", json={
        "slug": "acme", "email": "e3@acme.io", "password": "secret1"}).json()["access_token"]
    assert client.get("/api/digest", headers=_auth(emp)).status_code == 403
