from flask import (
    Flask, render_template, request, redirect, url_for, abort, flash,
    send_from_directory
)
from sqlalchemy import func, or_
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from pathlib import Path
import os, uuid

from dotenv import load_dotenv
load_dotenv()

from models import db, Entry, User
from forms import EntryForm, LoginForm


def create_app():
    app = Flask(__name__)
    # --- 設定 ---
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv("DB_URL", "sqlite:///diary.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-key"),
    )
    app.config.update(
        UPLOAD_FOLDER=os.getenv("UPLOAD_FOLDER", str(Path("uploads"))),
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,
    )

    # --- 拡張 ---
    CSRFProtect(app)
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db.create_all()

    # --- ヘルパ ---
    ALLOWED_EXTS = {"png", "jpg", "jpeg", "gif", "webp"}

    def save_image(file_storage):
        if not file_storage or file_storage.filename == "":
            return None
        fname = secure_filename(file_storage.filename)
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if ext not in ALLOWED_EXTS:
            raise ValueError("許可されていない拡張子です")
        new_name = f"{uuid.uuid4().hex}.{ext}"
        dest = Path(app.config["UPLOAD_FOLDER"]) / new_name
        file_storage.save(dest)
        return new_name

    # --- 静的配信 ---
    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # --- ルート ---
    @app.get("/")
    def index():
        q = request.args.get("q", "").strip()
        try:
            page = max(int(request.args.get("page", 1)), 1)
        except ValueError:
            page = 1
        per_page = 10

        base = db.select(Entry)
        if q:
            like = f"%{q.lower()}%"
            base = base.where(
                or_(
                    func.lower(Entry.title).like(like),
                    func.lower(Entry.body).like(like),
                )
            )
        count_stmt = db.select(func.count()).select_from(base.subquery())
        total = db.session.scalar(count_stmt) or 0
        total_pages = max((total + per_page - 1) // per_page, 1) if total else 1
        page = min(page, total_pages)

        stmt = base.order_by(Entry.created_at.desc()) \
                   .limit(per_page).offset((page - 1) * per_page)
        entries = db.session.execute(stmt).scalars().all()
        has_next = page < total_pages
        return render_template("index.html",
                               entries=entries, q=q,
                               page=page, has_next=has_next,
                               total=total, total_pages=total_pages,
                               user=current_user)

    # ---- 認証 ----
    @app.get("/login")
    def login():
        form = LoginForm()
        return render_template("login.html", form=form)

    @app.post("/login")
    def login_post():
        form = LoginForm()
        if form.validate_on_submit():
            u = db.session.execute(
                db.select(User).where(User.username == form.username.data.strip())
            ).scalar_one_or_none()
            if u and u.check_password(form.password.data):
                login_user(u)
                flash("ログインしました", "success")
                nxt = request.args.get("next")
                return redirect(nxt or url_for("index"))
            flash("ユーザー名またはパスワードが違います", "error")
            return render_template("login.html", form=form), 400
        return render_template("login.html", form=form), 400

    @app.post("/logout")
    @login_required
    def logout():
        logout_user()
        flash("ログアウトしました", "success")
        return redirect(url_for("index"))

    # ---- CRUD ----
    @app.get("/new")
    @login_required
    def new_entry():
        form = EntryForm()
        return render_template("new.html", form=form)

    @app.post("/create")
    @login_required
    def create_entry():
        form = EntryForm()
        if form.validate_on_submit():
            try:
                img_name = save_image(request.files.get("image"))
            except ValueError as e:
                flash(str(e), "error")
                return render_template("new.html", form=form), 400

            e = Entry(
                title=form.title.data.strip(),
                body=form.body.data.strip(),
                image_path=img_name,
            )
            db.session.add(e)
            db.session.commit()
            flash("作成しました", "success")
            return redirect(url_for("detail", entry_id=e.id))

        for field, errs in form.errors.items():
            for err in errs:
                flash(f"{field}: {err}", "error")
        return render_template("new.html", form=form), 400

    @app.get("/entry/<int:entry_id>")
    def detail(entry_id: int):
        e = db.session.get(Entry, entry_id)
        if not e:
            abort(404)
        return render_template("detail.html", e=e, user=current_user)

    @app.get("/entry/<int:entry_id>/edit")
    @login_required
    def edit_entry(entry_id: int):
        e = db.session.get(Entry, entry_id)
        if not e:
            abort(404)
        form = EntryForm(obj=e)
        return render_template("edit.html", form=form, e=e)

    @app.post("/entry/<int:entry_id>/update")
    @login_required
    def update_entry(entry_id: int):
        e = db.session.get(Entry, entry_id)
        if not e:
            abort(404)
        form = EntryForm()
        if form.validate_on_submit():
            e.title = form.title.data.strip()
            e.body = form.body.data.strip()

            file = request.files.get("image")
            if file and file.filename:
                try:
                    e.image_path = save_image(file)
                except ValueError as err:
                    flash(str(err), "error")
                    return render_template("edit.html", form=form, e=e), 400

            db.session.commit()
            flash("更新しました", "success")
            return redirect(url_for("detail", entry_id=e.id))

        for field, errs in form.errors.items():
            for err in errs:
                flash(f"{field}: {err}", "error")
        return render_template("edit.html", form=form, e=e), 400

    @app.post("/entry/<int:entry_id>/delete")
    @login_required
    def delete_entry(entry_id: int):
        e = db.session.get(Entry, entry_id)
        if not e:
            abort(404)
        db.session.delete(e)
        db.session.commit()
        flash("削除しました", "success")
        return redirect(url_for("index"))

    return app


app = create_app()
# 便利に参照できるように（任意）
app.db = db



# --- CLI: 初回の管理ユーザー作成 ---
import click
from models import db, User
from werkzeug.security import generate_password_hash

@app.cli.command("create_admin")
@click.argument("username")
@click.argument("password")
def create_admin(username, password):
    """例: flask --app app create_admin admin 'Passw0rd!'"""
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print("既に存在します:", username)
            return
        u = User(username=username)
        # set_password() があればそれを使う。無ければ password_hash を直接設定
        if hasattr(u, "set_password"):
            u.set_password(password)
        else:
            u.password_hash = generate_password_hash(password)
        db.session.add(u)
        db.session.commit()
        print("作成OK:", username)

