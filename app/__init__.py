from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
import os

from app.config import Config
from app.models.track import Track  # noqa: F401  (モデル登録用)
from app.models.user import User  # noqa: F401  (モデル登録用)
from app.routes.auth import auth_bp
from app.routes.tracks import tracks_bp
from app.routes.api import api_bp

csrf = CSRFProtect()


def create_app():

    template_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../templates")
    )

    app = Flask(
        __name__,
        template_folder=template_dir
    )
    app.config.from_object(Config)

    # CSRF 保護を有効化（テスト時は config.WTF_CSRF_ENABLED=False で無効化）
    csrf.init_app(app)

    # DB テーブル作成は scripts/migrate.py に一本化。
    # テスト時は conftest.py の reset_database フィクスチャが create_all を実行する。

    app.register_blueprint(auth_bp)
    app.register_blueprint(tracks_bp)
    app.register_blueprint(api_bp)

    # ==============================
    # カスタムエラーハンドラー
    # ==============================

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("errors/500.html"), 500

    return app