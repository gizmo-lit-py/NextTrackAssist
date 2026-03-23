"""
マイグレーションランナー

docker-compose.yml の web コンテナ起動コマンドから呼び出される:
    sh -c "python scripts/migrate.py && gunicorn ..."

SQLAlchemy モデルの定義を元に、テーブルが存在しない場合のみ作成する。
既存テーブルは変更しないため、カラム追加等の破壊的変更は
migrations/001_initial.py 等の個別マイグレーションファイルを利用する。
"""

import sys

from app.extensions import Base, engine
from app.models.track import Track  # noqa: F401 - Base への登録に必要
from app.models.user import User   # noqa: F401 - Base への登録に必要


def run():
    print("[migrate] テーブルの確認・作成を開始します...")
    try:
        Base.metadata.create_all(bind=engine)
        print("[migrate] 完了しました。")
    except Exception as e:
        print(f"[migrate] エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
