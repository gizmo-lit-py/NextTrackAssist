from flask import Flask
import os

from app.routes.auth import auth_bp
from app.routes.tracks import tracks_bp


def create_app():

    # templatesフォルダの絶対パスを取得
    template_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../templates")
    )

    # Flaskアプリ作成
    app = Flask(
        __name__,
        template_folder=template_dir
    )

    # Blueprint登録
    app.register_blueprint(auth_bp)
    app.register_blueprint(tracks_bp)

    return app