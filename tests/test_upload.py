import os, re, io, tempfile
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
    login_as_alice(app, c)  # ← 追加

    r = c.get("/new")
    token = extract_csrf(r.data)

    import io
    file_content = io.BytesIO(b"\x89PNG\r\n\x1a\nfakepng")
    data = {
        "title":"With Image","body":"body",
        "csrf_token":token,
        "image": (file_content, "x.png"),
    }
    r2 = c.post("/create", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert r2.status_code == 200
    html = r2.get_data(as_text=True)
    assert "With Image" in html and "/uploads/" in html

    with app.app_context():
        e = db.session.query(Entry).first()
        assert e.image_path is not None
