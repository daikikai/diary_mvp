import os, re
os.environ["DB_URL"] = "sqlite:///:memory:"

from app import create_app
from models import db, User

def csrf(html: bytes) -> str:
    m = re.search(rb'name="csrf_token".*?value="([^"]+)"', html, re.S)
    assert m, "csrf_token not found"
    return m.group(1).decode()

def make_app_with_user():
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        u = User(username="alice")
        u.set_password("pass1234")
        db.session.add(u); db.session.commit()
    return app

def test_login_required_and_login_flow():
    app = make_app_with_user()
    c = app.test_client()

    # 未ログイン→/new はログインへリダイレクト
    r = c.get("/new", follow_redirects=False)
    assert r.status_code in (302, 401, 403)
    assert "/login" in r.headers.get("Location", "")

    # ログイン
    r = c.get("/login")
    token = csrf(r.data)
    r2 = c.post("/login", data={
        "username": "alice", "password": "pass1234", "csrf_token": token
    }, follow_redirects=True)
    assert r2.status_code == 200
    assert "ログインしました" in r2.get_data(as_text=True)

    # ログイン後は /new に入れる
    r3 = c.get("/new")
    assert r3.status_code == 200

    # ログアウト
    token2 = csrf(r3.data)  # baseのフォームにもcsrfがある
    r4 = c.post("/logout", data={"csrf_token": token2}, follow_redirects=True)
    assert r4.status_code == 200
