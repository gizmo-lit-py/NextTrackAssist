from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
import os

from app.config import Config
from app.extensions import Base, engine
from app.models.track import Track  # noqa: F401
from app.models.user import User  # noqa: F401
from app.routes.auth import auth_bp
from app.routes.tracks import tracks_bp

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

    # 開発時に最低限アプリを立ち上げやすくするための自動作成。
    # 本番/運用では migrations/ 配下の migration を正とする。
    Base.metadata.create_all(bind=engine)

    app.register_blueprint(auth_bp)
    app.register_blueprint(tracks_bp)

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