"""
認証機能のテスト（register / login / logout）
"""

from werkzeug.security import generate_password_hash

from app.extensions import SessionLocal
from app.models.user import User


# ==============================
# ヘルパー
# ==============================

def register(client, email="new@example.com", password="securepass"):
    return client.post(
        "/register",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def login(client, email="dj@example.com", password="password123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


# ==============================
# 登録テスト
# ==============================

def test_register_success(client):
    """正常な登録でログインページにリダイレクトされること。"""
    response = register(client)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    db = SessionLocal()
    user = db.query(User).filter(User.email == "new@example.com").first()
    db.close()
    assert user is not None


def test_register_duplicate_email(client):
    """同一メールアドレスでの2重登録はエラーになること。"""
    register(client)
    response = register(client, follow_redirects=True) if False else client.post(
        "/register",
        data={"email": "new@example.com", "password": "securepass"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert "すでに登録済み" in body


def test_register_short_password(client):
    """パスワードが8文字未満の場合はエラーになること。"""
    response = client.post(
        "/register",
        data={"email": "short@example.com", "password": "abc"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert "8文字以上" in body

    db = SessionLocal()
    user = db.query(User).filter(User.email == "short@example.com").first()
    db.close()
    assert user is None


# ==============================
# ログインテスト
# ==============================

def test_login_success(client, user_with_tracks):
    """正しい認証情報でトラック一覧にリダイレクトされること。"""
    response = login(client)
    assert response.status_code == 302
    assert "/" in response.headers["Location"]


def test_login_wrong_password(client, user_with_tracks):
    """パスワードが間違っている場合はエラーメッセージが表示されること。"""
    response = client.post(
        "/login",
        data={"email": "dj@example.com", "password": "wrongpassword"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert "メールアドレスまたはパスワードが違います" in body


def test_logout_redirects_to_login(client, user_with_tracks):
    """ログアウト後にログインページへリダイレクトされること。"""
    login(client)
    response = client.post("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
