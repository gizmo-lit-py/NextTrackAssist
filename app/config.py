import os


class Config:

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://gizmo@localhost/nexttrack_db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # テスト時は環境変数 WTF_CSRF_ENABLED=False で無効化できる
    WTF_CSRF_ENABLED = os.getenv("WTF_CSRF_ENABLED", "True").lower() == "true"