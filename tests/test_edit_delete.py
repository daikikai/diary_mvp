import os, re
os.environ["DB_URL"] = "sqlite:///:memory:"

from app import create_app
from models import db, Entry
from models import db, Entry, User

def login_as_alice(app, client):
    with app.app_context():
        if not db.session.execute(db.select(User).where(User.username=="alice")).scalar_one_or_none():
            u = User(username="alice"); u.set_password("pass1234")
            db.session.add(u); db.session.commit()
    r = client.get("/login")
    import re
    token = re.search(rb'name="csrf_token".*?value="([^"]+)"', r.data, re.S).group(1).decode()
    client.post("/login", data={"username":"alice","password":"pass1234","csrf_token":token}, follow_redirects=True)

def make_app_with_one():
    app = create_app()
    app.config.update(TESTING=True)  # CSRFは有効のまま
    with app.app_context():
        db.create_all()
        e = Entry(title="Before", body="Old body")
        db.session.add(e)
        db.session.commit()
    return app

def extract_csrf(html_bytes: bytes) -> str:
    m = re.search(rb'name="csrf_token".*?value="([^"]+)"', html_bytes, re.S)
    assert m, "csrf_token not found"
    return m.group(1).decode()

def test_edit_update_ok():
    app = make_app_with_one()
    c = app.test_client()
    login_as_alice(app, c)  # ← 追加

    r = c.get("/entry/1/edit")
    assert r.status_code == 200
    token = extract_csrf(r.data)

    r2 = c.post("/entry/1/update", data={
        "title":"After","body":"New body","csrf_token":token
    }, follow_redirects=True)
    assert r2.status_code == 200
    html = r2.get_data(as_text=True)
    assert "更新しました" in html and "After" in html

    with app.app_context():
        e = db.session.get(Entry, 1)
        assert e.title=="After" and e.body=="New body"

def test_delete_ok_with_csrf():
    app = make_app_with_one()
    c = app.test_client()
    login_as_alice(app, c)  # ← 追加

    r = c.get("/entry/1")
    assert r.status_code == 200
    token = extract_csrf(r.data)

    r2 = c.post("/entry/1/delete", data={"csrf_token":token}, follow_redirects=True)
    assert r2.status_code == 200
    assert "削除しました" in r2.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(Entry, 1) is None

