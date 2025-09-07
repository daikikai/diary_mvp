import os, re
os.environ["DB_URL"] = "sqlite:///:memory:"

from app import create_app
from models import db, Entry

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

    # 1) 編集フォームGET（EntryForm経由のトークン）
    r = c.get("/entry/1/edit")
    assert r.status_code == 200
    token = extract_csrf(r.data)

    # 2) POST更新（CSRFトークン同梱）
    r2 = c.post("/entry/1/update", data={
        "title": "After",
        "body": "New body",
        "csrf_token": token
    }, follow_redirects=True)
    assert r2.status_code == 200

    # 日本語メッセージは bytes でなく文字列として比較
    html = r2.get_data(as_text=True)
    assert "更新しました" in html
    assert "After" in html  # 詳細ページに反映

    # DB確認
    with app.app_context():
        e = db.session.get(Entry, 1)
        assert e.title == "After"
        assert e.body == "New body"

def test_delete_ok_with_csrf():
    app = make_app_with_one()
    c = app.test_client()

    # 1) 詳細ページGET→ csrf_token() を抽出（detail.htmlの hidden から）
    r = c.get("/entry/1")
    assert r.status_code == 200
    token = extract_csrf(r.data)

    # 2) POST削除
    r2 = c.post("/entry/1/delete", data={"csrf_token": token}, follow_redirects=True)
    assert r2.status_code == 200

    # ここも文字列で比較
    html = r2.get_data(as_text=True)
    assert "削除しました" in html

    # DB確認
    with app.app_context():
        assert db.session.get(Entry, 1) is None
