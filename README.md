# diary_mvp

[![Python tests](https://github.com/daikikai/diary_mvp/actions/workflows/python-tests.yml/badge.svg)](https://github.com/daikikai/diary_mvp/actions/workflows/python-tests.yml)

Flask + SQLAlchemy の最小日記アプリ（CRUD/検索/ページング/CSRF/画像アップロード/pytest）。

## セットアップ
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
