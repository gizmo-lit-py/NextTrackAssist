"""
REST API エンドポイントのテスト

カバーしている観点:
  - 未ログインで 302 リダイレクト（認証ガード）
  - トラック一覧の正常取得
  - 推薦APIの正常レスポンス
"""

from werkzeug.security import generate_password_hash

from app.extensions import SessionLocal
from app.models.track import Track
from app.models.user import User


def _create_user_and_login(client):
    """テスト用ユーザーを作成してログインし、user_id を返す。"""
    db = SessionLocal()
    user = User(
        email="api_test@example.com",
        password_hash=generate_password_hash("password123"),
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    client.post("/login", data={"email": "api_test@example.com", "password": "password123"})
    return user_id


def _add_tracks(user_id, count=3):
    """指定ユーザーにテストトラックを追加し、IDリストを返す。"""
    db = SessionLocal()
    keys = ["8A", "9A", "8B"]
    tracks = [
        Track(
            user_id=user_id,
            title=f"API Track {i+1}",
            artist=f"Artist {i+1}",
            bpm=126 + i * 2,
            key=keys[i % len(keys)],
            energy=5,
        )
        for i in range(count)
    ]
    db.add_all(tracks)
    db.commit()
    ids = [t.id for t in tracks]
    db.close()
    return ids


# ==============================
# GET /api/tracks
# ==============================

def test_unauthenticated_redirects(client):
    """未ログインで /api/tracks にアクセスすると 302 リダイレクトされること。"""
    resp = client.get("/api/tracks")
    assert resp.status_code == 302


def test_list_tracks_returns_user_tracks(client):
    """ログイン済みユーザーのトラックが JSON で返ること。"""
    user_id = _create_user_and_login(client)
    _add_tracks(user_id, count=3)

    resp = client.get("/api/tracks")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 3
    assert "title" in data[0]
    assert "bpm" in data[0]


# ==============================
# GET /api/recommend/<track_id>
# ==============================

def test_recommend_success(client):
    """推薦APIが正常な構造の JSON を返すこと。"""
    user_id = _create_user_and_login(client)
    track_ids = _add_tracks(user_id, count=3)

    resp = client.get(f"/api/recommend/{track_ids[0]}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "base_track" in data
    assert "recommendations" in data
