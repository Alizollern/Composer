"""Тесты HTTP-API: регистрация/вход, RBAC, изоляция тенантов, чат через API."""


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
    quiz = r.json()["questions"]
    assert quiz and len(quiz[0]["options"]) == 4
    # оценивание: верный ответ -> зачёт
    correct = [quiz[0]["correct_index"]]
    g = client.post("/api/quiz/grade", headers=_auth(owner),
                    json={"quiz": quiz, "answers": correct})
    assert g.status_code == 200
    assert g.json()["correct"] == 1


def test_employee_cannot_generate_quiz(client):
    owner = _register(client)["access_token"]
    doc = client.post("/api/documents", headers=_auth(owner), json={
        "title": "Док", "content": "Эспрессо при 92 градуса."}).json()
    client.post("/api/users", headers=_auth(owner), json={
        "email": "w@acme.io", "password": "secret1", "role": "employee"})
    emp = client.post("/api/auth/login", json={
        "slug": "acme", "email": "w@acme.io", "password": "secret1"}).json()["access_token"]
    r = client.post(f"/api/documents/{doc['id']}/quiz", headers=_auth(emp),
                    json={"num_questions": 1})
    assert r.status_code == 403


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
