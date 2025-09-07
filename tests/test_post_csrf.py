import os, re
os.environ["DB_URL"] = "sqlite:///:memory:"

from app import create_app
from models import db, Entry

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

    # 1) フォームGET → トークン抽出
    r = client.get("/new")
    assert r.status_code == 200
    token = extract_csrf(r.data)

    # 2) トークン同梱でPOST
    r2 = client.post("/create", data={
        "title": "CSRF OK",
        "body": "with token",
        "csrf_token": token
    }, follow_redirects=True)
    assert r2.status_code == 200
    assert b"CSRF OK" in r2.data

    # 3) DBに保存されたことを確認
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
