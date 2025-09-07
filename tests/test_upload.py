import os, re, io, tempfile
os.environ["DB_URL"] = "sqlite:///:memory:"

from app import create_app
from models import db, Entry

def extract_csrf(html: bytes) -> str:
    m = re.search(rb'name="csrf_token".*?value="([^"]+)"', html, re.S)
    assert m, "csrf_token not found"
    return m.group(1).decode()

def make_app_tmp_upload():
    app = create_app()
    app.config.update(TESTING=True)
    tmp = tempfile.mkdtemp(prefix="up_")
    app.config["UPLOAD_FOLDER"] = tmp
    with app.app_context():
        db.create_all()
    return app

def test_create_with_image():
    app = make_app_tmp_upload()
    c = app.test_client()

    # フォームGET→トークン取得
    r = c.get("/new")
    token = extract_csrf(r.data)

    # ダミーPNG（中身はダミーでOK、拡張子チェックのみ）
    file_content = io.BytesIO(b"\x89PNG\r\n\x1a\nfakepng")
    data = {
        "title": "With Image",
        "body": "body",
        "csrf_token": token,
        "image": (file_content, "x.png"),
    }
    r2 = c.post("/create", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert r2.status_code == 200
    html = r2.get_data(as_text=True)
    assert "With Image" in html
    assert "/uploads/" in html

    # DBと実ファイル確認
    with app.app_context():
        e = db.session.query(Entry).first()
        assert e.image_path is not None
        assert os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], e.image_path))
