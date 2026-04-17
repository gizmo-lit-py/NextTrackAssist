import os


class Config:

    # 本番では必ず SECRET_KEY を環境変数で設定すること。
    # 未設定時は起動を拒否する（開発時は FLASK_ENV=development でフォールバック許可）。
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if os.getenv("FLASK_ENV") == "development":
            SECRET_KEY = "dev-secret-key"
        else:
            raise RuntimeError(
                "SECRET_KEY is not set. "
                "Set the SECRET_KEY environment variable before starting the app. "
                "(Hint: FLASK_ENV=development で開発用フォールバックを許可できます)"
            )

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://gizmo@localhost/nexttrack_db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # テスト時は環境変数 WTF_CSRF_ENABLED=False で無効化できる
    WTF_CSRF_ENABLED = os.getenv("WTF_CSRF_ENABLED", "True").lower() == "true"
