import os, re
os.environ["DB_URL"] = "sqlite:///:memory:"

from app import create_app
from models import db, Entry
from models import db, User

def login_as_alice(app, client):
    with app.app_context():
        db.create_all()
        u = User(username="alice"); u.set_password("pass1234")
        db.session.add(u); db.session.commit()
    r = client.get("/login")
    import re
    m = re.search(rb'name="csrf_token".*?value="([^"]+)"', r.data, re.S)
    token = m.group(1).decode()
    client.post("/login", data={"username":"alice","password":"pass1234","csrf_token":token}, follow_redirects=True)

def make_app():
    app = create_app()
    app.config.update(TESTING=True)  # CSRFは有効のまま（デフォルト）
    with app.app_context():
        db.create_all()
    return app

def extract_csrf(html: bytes) -> str:
    m = re.search(rb'name="csrf_token".*?value="([^"]+)"', html, re.S)
    assert m, "csrf_token not found in form"
    return m.group(1).decode()

def test_create_entry_csrf_ok():
    app = make_app()
    client = app.test_client()
    login_as_alice(app, client)  # ← 追加

    r = client.get("/new")
    assert r.status_code == 200
    token = extract_csrf(r.data)

    r2 = client.post("/create", data={
        "title":"CSRF OK","body":"with token","csrf_token":token
    }, follow_redirects=True)
    assert r2.status_code == 200
    html = r2.get_data(as_text=True)
    assert "CSRF OK" in html

    with app.app_context():
        assert db.session.query(Entry).count() == 1

def test_create_entry_csrf_missing_is_400():
    app = make_app()
    client = app.test_client()

    # トークン無し→バリデーション失敗で 400
    r = client.post("/create", data={
        "title": "Should Fail",
        "body": "No token",
    }, follow_redirects=False)
    assert r.status_code == 400
