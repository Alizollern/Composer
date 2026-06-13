"""Тесты M3: учебные треки, зачисление, прогресс, гейт по тесту, RBAC/изоляция."""


def _register(client, slug="acme", email="owner@acme.io", pw="secret1"):
    r = client.post("/api/auth/register-company", json={
        "company_name": slug.title(), "slug": slug,
        "owner_email": email, "owner_password": pw, "owner_name": "Босс"})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _make_employee(client, owner_tok, slug="acme", email="w@acme.io", pw="secret1"):
    client.post("/api/users", headers=_auth(owner_tok), json={
        "email": email, "password": pw, "role": "employee"})
    me = client.get("/api/auth/me", headers=_auth(
        client.post("/api/auth/login", json={
            "slug": slug, "email": email, "password": pw}).json()["access_token"]))
    tok = client.post("/api/auth/login", json={
        "slug": slug, "email": email, "password": pw}).json()["access_token"]
    return tok, me.json()["user_id"]


def _doc(client, owner_tok, title="Стандарт кофе",
         content="Эспрессо готовим при температуре 92 градуса."):
    return client.post("/api/documents", headers=_auth(owner_tok), json={
        "title": title, "content": content}).json()


def test_build_publish_enroll_and_pass_track(client):
    owner = _register(client)["access_token"]
    doc = _doc(client, owner)
    emp_tok, emp_id = _make_employee(client, owner)

    # owner собирает трек из одного шага с тестом
    track = client.post("/api/tracks", headers=_auth(owner), json={
        "title": "Онбординг бариста", "description": "Базовые стандарты"})
    assert track.status_code == 201, track.text
    track_id = track.json()["id"]

    step = client.post(f"/api/tracks/{track_id}/steps", headers=_auth(owner), json={
        "document_id": doc["id"], "require_quiz": True,
        "pass_score": 0.8, "num_questions": 1})
    assert step.status_code == 201, step.text

    # публикуем — теперь сотрудник его видит
    client.post(f"/api/tracks/{track_id}/status", headers=_auth(owner),
                json={"status": "published"})
    visible = client.get("/api/tracks", headers=_auth(emp_tok)).json()
    assert any(t["id"] == track_id for t in visible)

    # owner зачисляет сотрудника
    enr = client.post(f"/api/tracks/{track_id}/enroll", headers=_auth(owner),
                      json={"user_id": emp_id})
    assert enr.status_code == 201, enr.text
    enrollment_id = enr.json()["id"]

    # сотрудник видит зачисление, шаг ещё pending
    mine = client.get("/api/my/enrollments", headers=_auth(emp_tok)).json()
    assert len(mine) == 1
    step_id = mine[0]["steps"][0]["id"]
    assert mine[0]["steps"][0]["progress"]["status"] == "pending"

    # генерируем тест по документу шага и сдаём верно (ответы — по токену,
    # верный вариант узнаём из разбора, а не из выдачи теста)
    token = client.post(f"/api/documents/{doc['id']}/quiz", headers=_auth(owner),
                        json={"num_questions": 1}).json()["quiz_token"]
    probe = client.post("/api/quiz/grade", headers=_auth(owner),
                        json={"quiz_token": token, "answers": [0]}).json()
    answers = [probe["details"][0]["correct_index"]]
    sub = client.post(
        f"/api/enrollments/{enrollment_id}/steps/{step_id}/submit",
        headers=_auth(emp_tok), json={"quiz_token": token, "answers": answers})
    assert sub.status_code == 200, sub.text
    body = sub.json()
    assert body["step_status"] == "passed"
    assert body["enrollment_status"] == "completed"
    assert body["grade"]["correct"] == 1

    # прогресс виден управляющему
    prog = client.get(f"/api/tracks/{track_id}/progress", headers=_auth(owner)).json()
    assert prog[0]["passed_steps"] == 1 and prog[0]["total_steps"] == 1
    assert prog[0]["status"] == "completed"


def test_failing_quiz_keeps_step_pending(client):
    owner = _register(client)["access_token"]
    doc = _doc(client, owner)
    emp_tok, emp_id = _make_employee(client, owner)
    track_id = client.post("/api/tracks", headers=_auth(owner),
                           json={"title": "T"}).json()["id"]
    client.post(f"/api/tracks/{track_id}/steps", headers=_auth(owner), json={
        "document_id": doc["id"], "require_quiz": True, "pass_score": 0.8,
        "num_questions": 1})
    enr = client.post(f"/api/tracks/{track_id}/enroll", headers=_auth(owner),
                      json={"user_id": emp_id}).json()
    mine = client.get("/api/my/enrollments", headers=_auth(emp_tok)).json()
    step_id = mine[0]["steps"][0]["id"]
    token = client.post(f"/api/documents/{doc['id']}/quiz", headers=_auth(owner),
                        json={"num_questions": 1}).json()["quiz_token"]
    probe = client.post("/api/quiz/grade", headers=_auth(owner),
                        json={"quiz_token": token, "answers": [0]}).json()
    wrong = [(probe["details"][0]["correct_index"] + 1) % 4]
    sub = client.post(
        f"/api/enrollments/{enr['id']}/steps/{step_id}/submit",
        headers=_auth(emp_tok), json={"quiz_token": token, "answers": wrong}).json()
    assert sub["step_status"] == "pending"
    assert sub["enrollment_status"] == "active"


def test_step_without_quiz_passes_immediately(client):
    owner = _register(client)["access_token"]
    doc = _doc(client, owner)
    emp_tok, emp_id = _make_employee(client, owner)
    track_id = client.post("/api/tracks", headers=_auth(owner),
                           json={"title": "T"}).json()["id"]
    client.post(f"/api/tracks/{track_id}/steps", headers=_auth(owner), json={
        "document_id": doc["id"], "require_quiz": False})
    enr = client.post(f"/api/tracks/{track_id}/enroll", headers=_auth(owner),
                      json={"user_id": emp_id}).json()
    mine = client.get("/api/my/enrollments", headers=_auth(emp_tok)).json()
    step_id = mine[0]["steps"][0]["id"]
    sub = client.post(
        f"/api/enrollments/{enr['id']}/steps/{step_id}/submit",
        headers=_auth(emp_tok), json={}).json()
    assert sub["step_status"] == "passed"
    assert sub["enrollment_status"] == "completed"


def test_employee_cannot_create_track(client):
    owner = _register(client)["access_token"]
    emp_tok, _ = _make_employee(client, owner)
    r = client.post("/api/tracks", headers=_auth(emp_tok), json={"title": "T"})
    assert r.status_code == 403


def test_employee_cannot_submit_others_enrollment(client):
    owner = _register(client)["access_token"]
    doc = _doc(client, owner)
    tok_a, id_a = _make_employee(client, owner, email="a@acme.io")
    tok_b, id_b = _make_employee(client, owner, email="b@acme.io")
    track_id = client.post("/api/tracks", headers=_auth(owner),
                           json={"title": "T"}).json()["id"]
    client.post(f"/api/tracks/{track_id}/steps", headers=_auth(owner), json={
        "document_id": doc["id"], "require_quiz": False})
    enr_a = client.post(f"/api/tracks/{track_id}/enroll", headers=_auth(owner),
                        json={"user_id": id_a}).json()
    mine_a = client.get("/api/my/enrollments", headers=_auth(tok_a)).json()
    step_id = mine_a[0]["steps"][0]["id"]
    # B пытается сдать шаг в зачислении A
    r = client.post(
        f"/api/enrollments/{enr_a['id']}/steps/{step_id}/submit",
        headers=_auth(tok_b), json={})
    assert r.status_code == 403


def test_track_tenant_isolation(client):
    a = _register(client, slug="acme", email="a@a.io")["access_token"]
    b = _register(client, slug="beta", email="b@b.io")["access_token"]
    track_id = client.post("/api/tracks", headers=_auth(a),
                           json={"title": "Секретный трек A"}).json()["id"]
    # B не видит трек A и не может его открыть
    assert client.get("/api/tracks", headers=_auth(b)).json() == []
    assert client.get(f"/api/tracks/{track_id}", headers=_auth(b)).status_code == 404
