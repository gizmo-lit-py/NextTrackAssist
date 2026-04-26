"""
マイグレーションランナー

docker-compose.yml の web コンテナ起動コマンドから呼び出される:
    sh -c "python scripts/migrate.py && gunicorn ..."

1. SQLAlchemy モデルの定義を元に、テーブルが存在しない場合のみ作成する。
2. migrations/ 配下の追加マイグレーション（002_*.py 以降）を順番に呼び出す。
   各マイグレーションは冪等（重複実行しても安全）に書くこと。
"""

import importlib
import sys

from app.extensions import Base, engine
from app.models.track import Track  # noqa: F401 - Base への登録に必要
from app.models.user import User   # noqa: F401 - Base への登録に必要

# 追加マイグレーションは番号順にここへ追加していく。
# Python のモジュール名は数字で始められないので importlib で動的にロードする。
ADDITIONAL_MIGRATION_MODULES = [
    "migrations.002_bpm_float",
]
ADDITIONAL_MIGRATIONS = [importlib.import_module(name) for name in ADDITIONAL_MIGRATION_MODULES]


def run():
    print("[migrate] テーブルの確認・作成を開始します...")
    try:
        Base.metadata.create_all(bind=engine)
        for module in ADDITIONAL_MIGRATIONS:
            module.upgrade(engine)
        print("[migrate] 完了しました。")
    except Exception as e:
        print(f"[migrate] エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
