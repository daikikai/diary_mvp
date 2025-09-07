import os, sys
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from models import db, Entry


def make_app_with_data():
    app = create_app()
    with app.app_context():
        db.create_all()
        db.session.add_all([
            Entry(title="Hello", body="World"),
            Entry(title="Flask Diary", body="searchable text"),
        ])
        db.session.commit()
    return app

def test_index_and_search():
    app = make_app_with_data()
    client = app.test_client()

    # 一覧
    r = client.get("/")
    assert r.status_code == 200
    assert b"Hello" in r.data

    # 検索 q=Diary でヒット（大文字小文字を気にしない）
    r = client.get("/?q=diary")
    assert r.status_code == 200
    assert b"Flask Diary" in r.data
    # "Hello"は含まれてもよい（フィルタ次第）だが、今回は含まれない想定
    assert b"Hello" not in r.data
