from flask import Flask
from app.config import Config
from app.extensions import engine, Base


def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)

    from app.routes.tracks import tracks_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(tracks_bp)
    app.register_blueprint(auth_bp)

    Base.metadata.create_all(bind=engine)

    return app