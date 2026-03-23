import os

import pytest
from werkzeug.security import generate_password_hash

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["WTF_CSRF_ENABLED"] = "False"  # テスト中は CSRF を無効化

from app import create_app  # noqa: E402
from app.extensions import Base, SessionLocal, engine  # noqa: E402
from app.models.track import Track  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def app():
    return create_app()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_with_tracks():
    db = SessionLocal()
    user = User(email="dj@example.com", password_hash=generate_password_hash("password123"))
    other_user = User(email="other@example.com", password_hash=generate_password_hash("password123"))
    db.add_all([user, other_user])
    db.commit()

    db.add_all([
        Track(user_id=user.id, title="Track A", artist="Artist 1", bpm=128, key="8A", energy=6),
        Track(user_id=user.id, title="Track B", artist="Artist 2", bpm=129, key="9A", energy=7),
        Track(user_id=other_user.id, title="Hidden Track", artist="Artist 3", bpm=130, key="10A", energy=8),
    ])
    db.commit()
    db.close()
    return user


@pytest.fixture()
def logged_in_client(client, user_with_tracks):
    """ログイン済みのテストクライアントを返す。"""
    client.post(
        "/login",
        data={"email": "dj@example.com", "password": "password123"},
    )
    return client, user_with_tracks