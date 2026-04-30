FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Python が /app 配下のモジュール（app/ など）を見つけられるようにする
ENV PYTHONPATH=/app

# Railway は PORT 環境変数でポートを動的に指定してくる。
# シェル形式の CMD を使うことで ${PORT:-8000} のような変数展開が使える。
# migrate.py でテーブル作成 → gunicorn 起動 の順番で実行する。
CMD python scripts/migrate.py && gunicorn -b 0.0.0.0:${PORT:-8000} "app:create_app()"
