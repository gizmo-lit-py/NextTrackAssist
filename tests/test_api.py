# ==========================================
# NextTrackAssist - REST API Tests
# ==========================================
#
# api.py の統合テスト。
# 全4エンドポイント（tracks / import / recommend / generate-set）を検証。
# ==========================================

import io
import json

from werkzeug.security import generate_password_hash

from app.extensions import SessionLocal
from app.models.track import Track
from app.models.user import User


# ==============================
# ヘルパー
# ==============================

def _create_user_and_login(client):
    """ユーザーを作成してログインし、user を返す。"""
    db = SessionLocal()
    user = User(
        email="api_test@example.com",
        password_hash=generate_password_hash("password123"),
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    client.post("/login", data={
        "email": "api_test@example.com",
        "password": "password123",
    })

    return user_id


def _add_tracks(user_id, count=5, base_bpm=126):
    """指定ユーザーにテストトラックを追加する。"""
    db = SessionLocal()
    keys = ["8A", "9A", "8B", "7A", "10A"]
    tracks = []
    for i in range(count):
        t = Track(
            user_id=user_id,
            title=f"API Track {i+1}",
            artist=f"API Artist {i+1}",
            bpm=base_bpm + i * 2,
            key=keys[i % len(keys)],
            energy=5 + (i % 5),
        )
        tracks.append(t)
    db.add_all(tracks)
    db.commit()

    track_ids = [t.id for t in tracks]
    db.close()
    return track_ids


# ==============================
# GET /api/tracks
# ==============================

class TestListTracksApi:
    """トラック一覧APIのテスト。"""

    def test_unauthenticated(self, client):
        """未ログインで 302 リダイレクト。"""
        resp = client.get("/api/tracks")
        assert resp.status_code == 302

    def test_empty_library(self, client):
        """トラックが0件のとき空配列を返す。"""
        _create_user_and_login(client)
        resp = client.get("/api/tracks")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_returns_user_tracks(self, client):
        """ログインユーザーのトラックのみ返す。"""
        user_id = _create_user_and_login(client)
        _add_tracks(user_id, count=3)

        resp = client.get("/api/tracks")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 3
        assert "title" in data[0]
        assert "bpm" in data[0]

    def test_does_not_return_other_user_tracks(self, client):
        """他ユーザーのトラックは返さない。"""
        user_id = _create_user_and_login(client)
        _add_tracks(user_id, count=2)

        # 別ユーザーのトラックを追加
        db = SessionLocal()
        other = User(
            email="other_api@example.com",
            password_hash=generate_password_hash("password123"),
        )
        db.add(other)
        db.commit()
        db.add(Track(
            user_id=other.id, title="Hidden", artist="X",
            bpm=130, key="8A", energy=5,
        ))
        db.commit()
        db.close()

        resp = client.get("/api/tracks")
        data = resp.get_json()
        assert len(data) == 2


# ==============================
# POST /api/import
# ==============================

class TestImportApi:
    """CSVインポートAPIのテスト。"""

    def test_no_file(self, client):
        """ファイル未添付で 400。"""
        _create_user_and_login(client)
        resp = client.post("/api/import")
        assert resp.status_code == 400

    def test_invalid_extension(self, client):
        """許可されない拡張子で 400。"""
        _create_user_and_login(client)
        data = {"csv_file": (io.BytesIO(b"data"), "test.xlsx")}
        resp = client.post("/api/import", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400
        assert "allowed" in resp.get_json()["error"].lower() or "Only" in resp.get_json()["error"]


# ==============================
# GET /api/recommend/<track_id>
# ==============================

class TestRecommendApi:
    """推薦APIのテスト。"""

    def test_track_not_found(self, client):
        """存在しないトラックIDで 404。"""
        _create_user_and_login(client)
        resp = client.get("/api/recommend/99999")
        assert resp.status_code == 404

    def test_recommend_success(self, client):
        """正常な推薦結果を返す。"""
        user_id = _create_user_and_login(client)
        track_ids = _add_tracks(user_id, count=5)

        resp = client.get(f"/api/recommend/{track_ids[0]}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "base_track" in data
        assert "recommendations" in data
        assert len(data["recommendations"]) > 0
        assert "total_score" in data["recommendations"][0]

    def test_recommend_sorted_by_score(self, client):
        """推薦結果がスコア降順でソートされている。"""
        user_id = _create_user_and_login(client)
        track_ids = _add_tracks(user_id, count=5)

        resp = client.get(f"/api/recommend/{track_ids[0]}")
        data = resp.get_json()
        scores = [r["total_score"] for r in data["recommendations"]]
        assert scores == sorted(scores, reverse=True)

    def test_no_other_tracks(self, client):
        """他にトラックがない場合 400。"""
        user_id = _create_user_and_login(client)
        _add_tracks(user_id, count=1)

        # 1件しかない → 推薦候補なし
        db = SessionLocal()
        track = db.query(Track).filter(Track.user_id == user_id).first()
        track_id = track.id
        db.close()

        resp = client.get(f"/api/recommend/{track_id}")
        assert resp.status_code == 400


# ==============================
# POST /api/generate-set
# ==============================

class TestGenerateSetApi:
    """セット生成APIのテスト。"""

    def test_no_json_body(self, client):
        """JSONボディなしで 400。"""
        _create_user_and_login(client)
        resp = client.post("/api/generate-set")
        assert resp.status_code == 400

    def test_invalid_start_bpm(self, client):
        """start_bpm 範囲外で 400。"""
        _create_user_and_login(client)
        resp = client.post(
            "/api/generate-set",
            data=json.dumps({"start_bpm": 10, "target_bpm": 130, "num_tracks": 5}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_invalid_num_tracks(self, client):
        """num_tracks 範囲外で 400。"""
        _create_user_and_login(client)
        resp = client.post(
            "/api/generate-set",
            data=json.dumps({"start_bpm": 126, "target_bpm": 134, "num_tracks": 50}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_successful_generation(self, client):
        """正常なセット生成。"""
        user_id = _create_user_and_login(client)
        _add_tracks(user_id, count=10)

        resp = client.post(
            "/api/generate-set",
            data=json.dumps({"start_bpm": 126, "target_bpm": 140, "num_tracks": 5}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "tracks" in data
        assert "bpm_curve" in data
        assert "energy_curve" in data
        assert "avg_score" in data
        assert data["total_tracks"] == 5
