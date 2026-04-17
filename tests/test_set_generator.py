# ==========================================
# NextTrackAssist - Set Generator Tests
# ==========================================
#
# set_generator.py の単体テスト。
# 貪欲法によるDJセット生成ロジックを検証する。
# ==========================================

from werkzeug.security import generate_password_hash

from app.extensions import SessionLocal
from app.models.track import Track
from app.models.user import User
from app.services.set_generator import (
    _bpm_curve_penalty,
    _expected_bpm,
    generate_dj_set,
)


# ==============================
# ヘルパー: テストユーザー + トラック作成
# ==============================

def _create_user_with_tracks(num_tracks=10, base_bpm=124):
    """テスト用ユーザーと指定数のトラックを作成する。"""
    db = SessionLocal()

    user = User(
        email="setgen@example.com",
        password_hash=generate_password_hash("password123"),
    )
    db.add(user)
    db.commit()

    keys = ["8A", "9A", "8B", "7A", "10A", "8A", "9B", "7B", "11A", "6A",
            "12A", "1A", "2A", "3A", "4A", "5A", "6B", "7A", "8A", "9A",
            "10B", "11B", "12B", "1B", "2B", "3B", "4B", "5B", "6A", "7A"]

    tracks = []
    for i in range(num_tracks):
        t = Track(
            user_id=user.id,
            title=f"Track {i+1}",
            artist=f"Artist {i+1}",
            bpm=base_bpm + i * 2,
            key=keys[i % len(keys)],
            energy=min(4 + (i % 7), 10),
        )
        tracks.append(t)

    db.add_all(tracks)
    db.commit()
    db.close()

    return user


# ==============================
# _expected_bpm テスト
# ==============================

class TestExpectedBpm:
    """期待BPM計算のテスト。"""

    def test_linear_interpolation(self):
        """残りステップ数に応じた線形補間が正しい。"""
        result = _expected_bpm(126, 134, 4)
        assert result == 128.0

    def test_remaining_zero(self):
        """remaining=0 のとき target_bpm を返す。"""
        result = _expected_bpm(126, 134, 0)
        assert result == 134.0

    def test_remaining_one(self):
        """remaining=1 のとき target_bpm を返す。"""
        result = _expected_bpm(126, 134, 1)
        assert result == 134.0

    def test_same_bpm(self):
        """start == target のとき変化なし。"""
        result = _expected_bpm(130, 130, 5)
        assert result == 130.0

    def test_decreasing_bpm(self):
        """target < current の場合も正しく計算。"""
        result = _expected_bpm(140, 120, 4)
        assert result == 135.0


# ==============================
# _bpm_curve_penalty テスト
# ==============================

class TestBpmCurvePenalty:
    """BPMカーブペナルティのテスト。"""

    def test_no_deviation(self):
        """BPMが期待値と一致 → ペナルティ0。"""
        assert _bpm_curve_penalty(128, 128.0) == 0

    def test_small_deviation(self):
        """2BPMズレ → ペナルティ6。"""
        assert _bpm_curve_penalty(130, 128.0) == 6.0

    def test_max_penalty(self):
        """大きなズレ → ペナルティ上限30。"""
        assert _bpm_curve_penalty(150, 128.0) == 30


# ==============================
# generate_dj_set テスト
# ==============================

class TestGenerateDjSet:
    """DJセット生成のテスト。"""

    def test_basic_generation(self):
        """基本的なセット生成が正しく動作する。"""
        user = _create_user_with_tracks(10, base_bpm=124)
        db = SessionLocal()

        try:
            result = generate_dj_set(
                db=db,
                user_id=user.id,
                start_bpm=124,
                target_bpm=140,
                num_tracks=5,
            )
        finally:
            db.close()

        assert result["total_tracks"] == 5
        assert len(result["tracks"]) == 5
        assert len(result["bpm_curve"]) == 5
        assert len(result["energy_curve"]) == 5
        assert isinstance(result["avg_score"], float)

    def test_first_track_closest_to_start_bpm(self):
        """最初のトラックが start_bpm に最も近い。"""
        user = _create_user_with_tracks(10, base_bpm=120)
        db = SessionLocal()

        try:
            result = generate_dj_set(
                db=db,
                user_id=user.id,
                start_bpm=126,
                target_bpm=140,
                num_tracks=3,
            )
        finally:
            db.close()

        first_bpm = result["tracks"][0]["bpm"]
        # 120, 122, 124, 126, 128, ... → 126が最も近い
        assert first_bpm == 126

    def test_no_duplicate_tracks(self):
        """生成されたセットに同じトラックが含まれない。"""
        user = _create_user_with_tracks(10, base_bpm=124)
        db = SessionLocal()

        try:
            result = generate_dj_set(
                db=db,
                user_id=user.id,
                start_bpm=124,
                target_bpm=140,
                num_tracks=8,
            )
        finally:
            db.close()

        ids = [t["id"] for t in result["tracks"]]
        assert len(ids) == len(set(ids))

    def test_not_enough_tracks(self):
        """トラック数不足のとき ValueError を投げる。"""
        user = _create_user_with_tracks(3, base_bpm=124)
        db = SessionLocal()

        try:
            import pytest
            with pytest.raises(ValueError, match="Not enough tracks"):
                generate_dj_set(
                    db=db,
                    user_id=user.id,
                    start_bpm=124,
                    target_bpm=140,
                    num_tracks=10,
                )
        finally:
            db.close()

    def test_invalid_num_tracks(self):
        """num_tracks < 2 のとき ValueError。"""
        user = _create_user_with_tracks(5, base_bpm=124)
        db = SessionLocal()

        try:
            import pytest
            with pytest.raises(ValueError, match="num_tracks must be at least 2"):
                generate_dj_set(
                    db=db,
                    user_id=user.id,
                    start_bpm=124,
                    target_bpm=140,
                    num_tracks=1,
                )
        finally:
            db.close()

    def test_first_track_has_no_score(self):
        """最初のトラックにはスコア情報がない（基準曲なので）。"""
        user = _create_user_with_tracks(5, base_bpm=124)
        db = SessionLocal()

        try:
            result = generate_dj_set(
                db=db,
                user_id=user.id,
                start_bpm=124,
                target_bpm=134,
                num_tracks=4,
            )
        finally:
            db.close()

        first = result["tracks"][0]
        assert "score" not in first

    def test_subsequent_tracks_have_scores(self):
        """2曲目以降にはスコア情報が含まれる。"""
        user = _create_user_with_tracks(10, base_bpm=124)
        db = SessionLocal()

        try:
            result = generate_dj_set(
                db=db,
                user_id=user.id,
                start_bpm=124,
                target_bpm=140,
                num_tracks=5,
            )
        finally:
            db.close()

        for track in result["tracks"][1:]:
            assert "score" in track
            assert "bpm_reason" in track
            assert "energy_reason" in track
            assert "key_reason" in track

    def test_avg_score_calculation(self):
        """avg_score がゼロでなく妥当な範囲。"""
        user = _create_user_with_tracks(10, base_bpm=124)
        db = SessionLocal()

        try:
            result = generate_dj_set(
                db=db,
                user_id=user.id,
                start_bpm=124,
                target_bpm=140,
                num_tracks=5,
            )
        finally:
            db.close()

        assert result["avg_score"] > 0
        assert result["avg_score"] <= 100
