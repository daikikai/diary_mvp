import os
os.environ["DB_URL"] = "sqlite:///:memory:"

from app import create_app
from models import db, Entry

def make_app_with_entries(n=25):
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        for i in range(n):
            db.session.add(Entry(title=f"T{i+1}", body="x"))
        db.session.commit()
    return app

def get_html(client, path):
    r = client.get(path)
    assert r.status_code == 200
    return r.get_data(as_text=True)

def test_pagination_shows_total_and_pages():
    app = make_app_with_entries(25)  # 25件、per_page=10 → 3ページ
    c = app.test_client()

    html1 = get_html(c, "/")
    assert "全25件" in html1
    assert "Page 1/3" in html1
    assert "次へ" in html1

    html2 = get_html(c, "/?page=2")
    assert "Page 2/3" in html2

    # 大きすぎるpage指定は最終ページに丸める
    html_last = get_html(c, "/?page=99")
    assert "Page 3/3" in html_last
    assert "次へ" not in html_last
