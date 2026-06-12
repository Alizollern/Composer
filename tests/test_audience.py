"""Тесты M1.5: аудитория стандартов (роль/точка) — список, ретривал бота, доступ."""


def _register(client, slug="acme", email="owner@acme.io", pw="secret1"):
    r = client.post("/api/auth/register-company", json={
        "company_name": slug.title(), "slug": slug,
        "owner_email": email, "owner_password": pw, "owner_name": "Босс"})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _employee(client, owner_tok, slug="acme", email="w@acme.io", pw="secret1",
              point_id=None):
    body = {"email": email, "password": pw, "role": "employee"}
    if point_id:
        body["point_id"] = point_id
    client.post("/api/users", headers=_auth(owner_tok), json=body)
    return client.post("/api/auth/login", json={
        "slug": slug, "email": email, "password": pw}).json()["access_token"]


def test_role_scoped_document_hidden_from_employee_list(client):
    owner = _register(client)["access_token"]
    emp = _employee(client, owner)
    # документ только для менеджеров
    client.post("/api/documents", headers=_auth(owner), json={
        "title": "Только для менеджеров",
        "content": "Код сейфа компании: 4321.",
        "audience_roles": ["manager"]})
    # общий документ
    client.post("/api/documents", headers=_auth(owner), json={
        "title": "Для всех", "content": "Эспрессо при 92 градуса."})
    # owner видит оба
    assert len(client.get("/api/documents", headers=_auth(owner)).json()) == 2
    # сотрудник — только общий
    emp_docs = client.get("/api/documents", headers=_auth(emp)).json()
    assert [d["title"] for d in emp_docs] == ["Для всех"]


def test_chat_does_not_leak_out_of_audience(client):
    owner = _register(client)["access_token"]
    emp = _employee(client, owner)
    client.post("/api/documents", headers=_auth(owner), json={
        "title": "Сейф", "content": "Код сейфа компании: 4321.",
        "audience_roles": ["manager"]})
    # сотрудник спрашивает про сейф — стандарт не его аудитории → отказ
    r = client.post("/api/chat", headers=_auth(emp),
                    json={"question": "какой код сейфа компании"})
    assert r.json()["refused"] is True
    # менеджер (owner) — получает ответ
    r2 = client.post("/api/chat", headers=_auth(owner),
                     json={"question": "какой код сейфа компании 4321"})
    assert r2.json()["refused"] is False


def test_point_scoped_document(client):
    owner = _register(client)["access_token"]
    # создаём точку напрямую через ORM недоступно из API — используем set_audience
    # через указание point_id; сотрудник без этой точки не должен видеть документ.
    doc = client.post("/api/documents", headers=_auth(owner), json={
        "title": "Стандарт точки", "content": "Особый регламент точки А."}).json()
    # назначаем документ на несуществующую у сотрудника точку
    r = client.post(f"/api/documents/{doc['id']}/audience", headers=_auth(owner),
                    json={"point_id": "point-A"})
    assert r.status_code == 200, r.text
    emp = _employee(client, owner)  # без point_id
    emp_docs = client.get("/api/documents", headers=_auth(emp)).json()
    assert emp_docs == []
    # прямой доступ по id тоже закрыт
    assert client.get(f"/api/documents/{doc['id']}",
                      headers=_auth(emp)).status_code == 404


def test_set_audience_then_visible(client):
    owner = _register(client)["access_token"]
    emp = _employee(client, owner)
    doc = client.post("/api/documents", headers=_auth(owner), json={
        "title": "Док", "content": "Текст.", "audience_roles": ["manager"]}).json()
    assert client.get("/api/documents", headers=_auth(emp)).json() == []
    # переназначаем аудиторию на всех — становится видно
    client.post(f"/api/documents/{doc['id']}/audience", headers=_auth(owner),
                json={"audience_roles": []})
    titles = [d["title"] for d in client.get("/api/documents", headers=_auth(emp)).json()]
    assert "Док" in titles
