import logging
import os

from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text

from app.config import Config
from app.extensions import SessionLocal
from app.models.track import Track  # noqa: F401  (モデル登録用)
from app.models.user import User  # noqa: F401  (モデル登録用)
from app.routes.auth import auth_bp
from app.routes.tracks import tracks_bp
from app.routes.api import api_bp

csrf = CSRFProtect()


def create_app():

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)


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
    # /api/* はセッション Cookie + Same-Origin 前提で運用する想定のため、
    # CSRF 保護の対象から外す。外部からクロスオリジンで叩く用途は現状サポート外。
    csrf.exempt(api_bp)

    # DB テーブル作成は scripts/migrate.py に一本化。
    # テスト時は conftest.py の reset_database フィクスチャが create_all を実行する。

    app.register_blueprint(auth_bp)
    app.register_blueprint(tracks_bp)
    app.register_blueprint(api_bp)

    # ==============================
    # セキュリティヘッダー
    # ==============================
    # Railway 本番は Nginx を経由しないため、Flask 側で全レスポンスに常時付与する。
    # nginx/prod.conf にも同等の設定があるが、こちらが「常に有効なソース」となる。

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        # HSTS は HTTPS リクエストのみに付与する。
        # Railway 等のリバースプロキシ配下では request.is_secure が False になるため、
        # X-Forwarded-Proto も併せて確認する。
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
        if request.is_secure or forwarded_proto == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response

    # ==============================
    # ヘルスチェック
    # ==============================
    # Railway / 外形監視 / ロードバランサー向けの死活監視エンドポイント。
    # アプリの起動だけでなく DB への到達まで SELECT 1 で確認する。

    @app.get("/healthz")
    def healthz():
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return jsonify({"status": "ok"}), 200
        except Exception:
            logger.exception("Health check failed")
            return jsonify({"status": "error"}), 503
        finally:
            db.close()

    # ==============================
    # カスタムエラーハンドラー
    # ==============================

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error("500 Internal Server Error: %s", e)
        return render_template("errors/500.html"), 500

    logger.info("App created (env=%s)", app.config.get("ENV", "production"))

    return app