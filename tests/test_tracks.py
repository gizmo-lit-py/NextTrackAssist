"""
トラック CRUD・バリデーション・推薦機能のテスト
"""

from werkzeug.security import generate_password_hash

from app.extensions import SessionLocal
from app.models.track import Track
from app.models.user import User


# ==============================
# ヘルパー
# ==============================

def login(client, email="dj@example.com", password="password123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def create_track(client, **kwargs):
    """デフォルト値付きのトラック登録ヘルパー。"""
    data = {
        "title": "Test Track",
        "artist": "Test Artist",
        "bpm": "128",
        "key": "8A",
        "energy": "6",
    }
    data.update(kwargs)
    return client.post("/tracks", data=data, follow_redirects=False)


# ==============================
# 認証ガードのテスト
# ==============================

def test_index_redirects_when_not_logged_in(client):
    """未ログイン状態でトップページにアクセスするとログインへリダイレクトされること。"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_new_track_form_requires_login(client):
    """未ログイン状態でトラック登録フォームにアクセスするとリダイレクトされること。"""
    response = client.get("/tracks/new", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ==============================
# トラック登録テスト
# ==============================

def test_create_track_success(logged_in_client):
    """正常なデータでトラックが登録されること。"""
    client, user = logged_in_client
    response = create_track(client)
    assert response.status_code == 302

    db = SessionLocal()
    track = db.query(Track).filter(Track.title == "Test Track").first()
    db.close()
    assert track is not None
    assert track.bpm == 128
    assert track.key == "8A"
    assert track.energy == 6


def test_create_track_bpm_too_low(logged_in_client):
    """BPM が 40 未満の場合は登録されないこと。"""
    client, _ = logged_in_client
    response = create_track(client, bpm="10", follow_redirects=True) if False else client.post(
        "/tracks",
        data={"title": "T", "artist": "A", "bpm": "10", "key": "8A", "energy": "6"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert "40" in body or "範囲" in body


def test_create_track_bpm_too_high(logged_in_client):
    """BPM が 250 超の場合は登録されないこと。"""
    client, _ = logged_in_client
    response = client.post(
        "/tracks",
        data={"title": "T", "artist": "A", "bpm": "300", "key": "8A", "energy": "6"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert "250" in body or "範囲" in body


def test_create_track_invalid_energy(logged_in_client):
    """Energy が範囲外（0 や 11）の場合は登録されないこと。"""
    client, _ = logged_in_client
    response = client.post(
        "/tracks",
        data={"title": "T", "artist": "A", "bpm": "128", "key": "8A", "energy": "11"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert "Energy" in body or "範囲" in body


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


def test_create_track_missing_title(logged_in_client):
    """Title が空の場合は登録されないこと。"""
    client, _ = logged_in_client
    response = client.post(
        "/tracks",
        data={"title": "", "artist": "A", "bpm": "128", "key": "8A", "energy": "6"},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert "Title" in body or "必須" in body


# ==============================
# トラック編集・削除テスト
# ==============================

def test_edit_track_success(logged_in_client):
    """自分のトラックを正常に更新できること。"""
    client, user = logged_in_client

    db = SessionLocal()
    track = db.query(Track).filter(Track.user_id == user.id).first()
    db.close()

    response = client.post(
        f"/tracks/{track.id}/update",
        data={"title": "Updated", "artist": "Updated Artist", "bpm": "130", "key": "9A", "energy": "7"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Updated" in body


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


def test_cannot_edit_other_users_track(logged_in_client):
    """他ユーザーのトラックを編集しようとすると 404 になること。"""
    client, _ = logged_in_client

    db = SessionLocal()
    hidden = db.query(Track).filter(Track.title == "Hidden Track").first()
    db.close()

    response = client.post(
        f"/tracks/{hidden.id}/update",
        data={"title": "Hacked", "artist": "Hacker", "bpm": "128", "key": "8A", "energy": "6"},
    )
    assert response.status_code == 404


def test_cannot_delete_other_users_track(logged_in_client):
    """他ユーザーのトラックを削除しようとすると 404 になること。"""
    client, _ = logged_in_client

    db = SessionLocal()
    hidden = db.query(Track).filter(Track.title == "Hidden Track").first()
    db.close()

    response = client.post(f"/tracks/{hidden.id}/delete")
    assert response.status_code == 404


# ==============================
# 推薦テスト
# ==============================

def test_recommend_returns_results(logged_in_client):
    """2曲以上ある状態で推薦が表示されること。"""
    client, user = logged_in_client

    db = SessionLocal()
    base_track = db.query(Track).filter(Track.user_id == user.id).first()
    db.close()

    response = client.get(f"/tracks/{base_track.id}/recommend", follow_redirects=True)
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "総合スコア" in body or "Score" in body


def test_recommend_no_candidates(client):
    """自分のトラックが1曲しかない場合、エラーメッセージが表示されること。"""
    db = SessionLocal()
    solo_user = User(email="solo@example.com", password_hash=generate_password_hash("password123"))
    db.add(solo_user)
    db.commit()
    track = Track(user_id=solo_user.id, title="Only Track", artist="Solo", bpm=128, key="8A", energy=6)
    db.add(track)
    db.commit()
    track_id = track.id
    db.close()

    login(client, "solo@example.com", "password123")
    response = client.get(f"/tracks/{track_id}/recommend", follow_redirects=True)
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "他のトラックがないため" in body
