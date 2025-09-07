from flask import (
    Flask, render_template, request, redirect, url_for, abort, flash,
    send_from_directory
)
from sqlalchemy import func, or_
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from pathlib import Path
import os, uuid

from dotenv import load_dotenv
load_dotenv()

from models import db, Entry
from forms import EntryForm


def create_app():
    app = Flask(__name__)
    # --- 設定（DB / SECRET_KEY / アップロード） ---
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv("DB_URL", "sqlite:///diary.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-key"),
    )
    app.config.update(
        UPLOAD_FOLDER=os.getenv("UPLOAD_FOLDER", str(Path("uploads"))),
        MAX_CONTENT_LENGTH=4 * 1024 * 1024,  # 4MB
    )

    # CSRFは設定直後に初期化（Jinja の csrf_token() を確実に有効化）
    CSRFProtect(app)

    # DB初期化とアップロード先の作成
    db.init_app(app)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db.create_all()

    # --- 画像保存ヘルパ（create_app 内に置く：app.config にアクセス可） ---
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

    # --- 静的配信（アップロード画像） ---
    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # --- ルーティング ---
    @app.get("/")
    def index():
        q = request.args.get("q", "").strip()
        try:
            page = max(int(request.args.get("page", 1)), 1)
        except ValueError:
            page = 1
        per_page = 10

        # 1) 基本クエリを作る（ここにフィルタを積む）
        base = db.select(Entry)
        if q:
            like = f"%{q.lower()}%"
            base = base.where(
                or_(
                    func.lower(Entry.title).like(like),
                    func.lower(Entry.body).like(like),
                )
            )

        # 2) 総件数と総ページ
        count_stmt = db.select(func.count()).select_from(base.subquery())
        total = db.session.scalar(count_stmt) or 0
        total_pages = max((total + per_page - 1) // per_page, 1) if total else 1

        # 3) page を範囲内にクランプ
        page = min(page, total_pages)

        # 4) ページングクエリ（並び→limit/offset）
        stmt = base.order_by(Entry.created_at.desc()) \
                   .limit(per_page).offset((page - 1) * per_page)
        entries = db.session.execute(stmt).scalars().all()

        has_next = page < total_pages
        return render_template(
            "index.html",
            entries=entries, q=q,
            page=page, has_next=has_next,
            total=total, total_pages=total_pages
        )


    @app.get("/new")
    def new_entry():
        form = EntryForm()
        return render_template("new.html", form=form)

    @app.post("/create")
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

        # バリデーション失敗時
        for field, errs in form.errors.items():
            for err in errs:
                flash(f"{field}: {err}", "error")
        return render_template("new.html", form=form), 400

    @app.get("/entry/<int:entry_id>")
    def detail(entry_id: int):
        e = db.session.get(Entry, entry_id)
        if not e:
            abort(404)
        return render_template("detail.html", e=e)

    @app.get("/entry/<int:entry_id>/edit")
    def edit_entry(entry_id: int):
        e = db.session.get(Entry, entry_id)
        if not e:
            abort(404)
        form = EntryForm(obj=e)
        return render_template("edit.html", form=form, e=e)

    @app.post("/entry/<int:entry_id>/update")
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
    def delete_entry(entry_id: int):
        e = db.session.get(Entry, entry_id)
        if not e:
            abort(404)
        db.session.delete(e)
        db.session.commit()
        flash("削除しました", "success")
        return redirect(url_for("index"))

    return app


# pytest/import用にモジュール末尾で1回だけ生成
app = create_app()
