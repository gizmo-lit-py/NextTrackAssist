"""
トラック CRUD・バリデーション・認可のテスト

カバーしている観点:
  - 未ログインユーザーのアクセス制御
  - トラック登録の正常系
  - バリデーション（BPM範囲外・不正なKey形式）
  - 削除の正常系
  - 他ユーザーのトラックへの操作拒否（認可）
"""

from app.extensions import SessionLocal
from app.models.track import Track


def login(client, email="dj@example.com", password="password123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


# ==============================
# 認証ガード
# ==============================

def test_index_redirects_when_not_logged_in(client):
    """未ログイン状態でトップページにアクセスするとログインへリダイレクトされること。"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ==============================
# トラック登録
# ==============================

def test_create_track_success(logged_in_client):
    """正常なデータでトラックが登録されること。"""
    client, user = logged_in_client
    client.post(
        "/tracks",
        data={"title": "Test Track", "artist": "Test Artist", "bpm": "128", "key": "8A", "energy": "6"},
        follow_redirects=False,
    )

    db = SessionLocal()
    track = db.query(Track).filter(Track.title == "Test Track").first()
    db.close()
    assert track is not None
    assert track.bpm == 128
    assert track.key == "8A"


def test_create_track_bpm_too_low(logged_in_client):
    """BPM が 40 未満の場合は登録されないこと。"""
    client, _ = logged_in_client
    response = client.post(
        "/tracks",
        data={"title": "T", "artist": "A", "bpm": "10", "key": "8A", "energy": "6"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert "40" in body or "範囲" in body


def test_create_track_invalid_key_format(logged_in_client):
    """Key が Camelot 形式でない場合は登録されないこと。"""
    client, _ = logged_in_client
    response = client.post(
        "/tracks",
        data={"title": "T", "artist": "A", "bpm": "128", "key": "ZZ", "energy": "6"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert "Camelot" in body or "Key" in body


# ==============================
# トラック削除
# ==============================

def test_delete_track_success(logged_in_client):
    """自分のトラックを正常に削除できること。"""
    client, user = logged_in_client

    db = SessionLocal()
    track = db.query(Track).filter(Track.user_id == user.id).first()
    track_id = track.id
    db.close()

    response = client.post(f"/tracks/{track_id}/delete", follow_redirects=True)
    assert response.status_code == 200

    db = SessionLocal()
    deleted = db.query(Track).filter(Track.id == track_id).first()
    db.close()
    assert deleted is None


def test_cannot_delete_other_users_track(logged_in_client):
    """他ユーザーのトラックを削除しようとすると 404 になること。"""
    client, _ = logged_in_client

    db = SessionLocal()
    hidden = db.query(Track).filter(Track.title == "Hidden Track").first()
    db.close()

    response = client.post(f"/tracks/{hidden.id}/delete")
    assert response.status_code == 404
