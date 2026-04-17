"""
セットリストビルダーのユニットテスト
=====================================
"""

import sys
import os

# パスを通す
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.setlist_builder import (
    calc_direction_score,
    calc_setlist_score,
    build_setlist,
    format_setlist_summary,
    DIRECTION_UP,
    DIRECTION_KEEP,
    DIRECTION_DOWN,
)


# ==============================
# テスト用のダミートラックデータ
# ==============================

SAMPLE_TRACKS = [
    {"id": 1,  "title": "Track A", "artist": "DJ A", "bpm": 70,  "key": "8A",  "energy": 5},
    {"id": 2,  "title": "Track B", "artist": "DJ B", "bpm": 72,  "key": "9A",  "energy": 6},
    {"id": 3,  "title": "Track C", "artist": "DJ C", "bpm": 75,  "key": "8A",  "energy": 6},
    {"id": 4,  "title": "Track D", "artist": "DJ D", "bpm": 78,  "key": "8B",  "energy": 7},
    {"id": 5,  "title": "Track E", "artist": "DJ E", "bpm": 80,  "key": "9A",  "energy": 7},
    {"id": 6,  "title": "Track F", "artist": "DJ F", "bpm": 85,  "key": "10A", "energy": 8},
    {"id": 7,  "title": "Track G", "artist": "DJ G", "bpm": 90,  "key": "10B", "energy": 8},
    {"id": 8,  "title": "Track H", "artist": "DJ H", "bpm": 95,  "key": "11A", "energy": 9},
    {"id": 9,  "title": "Track I", "artist": "DJ I", "bpm": 100, "key": "12A", "energy": 9},
    {"id": 10, "title": "Track J", "artist": "DJ J", "bpm": 128, "key": "8A",  "energy": 7},
    {"id": 11, "title": "Track K", "artist": "DJ K", "bpm": 130, "key": "9A",  "energy": 8},
    {"id": 12, "title": "Track L", "artist": "DJ L", "bpm": 132, "key": "9B",  "energy": 8},
    {"id": 13, "title": "Track M", "artist": "DJ M", "bpm": 135, "key": "10A", "energy": 9},
    {"id": 14, "title": "Track N", "artist": "DJ N", "bpm": 138, "key": "10B", "energy": 9},
    {"id": 15, "title": "Track O", "artist": "DJ O", "bpm": 140, "key": "11A", "energy": 10},
]


# ==============================
# calc_direction_score テスト
# ==============================

class TestDirectionScore:

    def test_up_positive_diff(self):
        """UP方向: BPMが上がればボーナス"""
        score = calc_direction_score(128, 130, DIRECTION_UP)
        assert score > 0

    def test_up_negative_diff(self):
        """UP方向: BPMが大きく下がればペナルティ"""
        score = calc_direction_score(128, 120, DIRECTION_UP)
        assert score < 0

    def test_up_small_negative(self):
        """UP方向: BPMがわずかに下がる(-2以内)はペナルティなし"""
        score = calc_direction_score(128, 126, DIRECTION_UP)
        assert score == 0

    def test_down_negative_diff(self):
        """DOWN方向: BPMが下がればボーナス"""
        score = calc_direction_score(128, 125, DIRECTION_DOWN)
        assert score > 0

    def test_down_positive_diff(self):
        """DOWN方向: BPMが大きく上がればペナルティ"""
        score = calc_direction_score(128, 135, DIRECTION_DOWN)
        assert score < 0

    def test_keep_within_range(self):
        """KEEP方向: BPMが±2以内ならボーナス"""
        score = calc_direction_score(128, 129, DIRECTION_KEEP)
        assert score > 0

    def test_keep_far_away(self):
        """KEEP方向: BPMが±6以上離れるとペナルティ"""
        score = calc_direction_score(128, 140, DIRECTION_KEEP)
        assert score < 0


# ==============================
# build_setlist テスト
# ==============================

class TestBuildSetlist:

    def test_empty_tracks(self):
        """トラックが空ならセットリストも空"""
        result = build_setlist([], start_bpm=128)
        assert result["total_tracks"] == 0
        assert result["setlist"] == []

    def test_basic_build(self):
        """基本: セットリストが生成される"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=128, set_length_minutes=20)
        assert result["total_tracks"] > 0
        assert len(result["setlist"]) > 0

    def test_first_track_closest_bpm(self):
        """1曲目は開始BPMに最も近い曲が選ばれる"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=70)
        first = result["setlist"][0]["track"]
        assert first["bpm"] == 70  # Track A

    def test_first_track_closest_bpm_128(self):
        """開始BPM128なら、BPM128の曲が1曲目"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=128)
        first = result["setlist"][0]["track"]
        assert first["bpm"] == 128  # Track J

    def test_no_duplicate_tracks(self):
        """同じ曲がセットリストに2回出ない"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=128, set_length_minutes=60)
        track_ids = [e["track"]["id"] for e in result["setlist"]]
        assert len(track_ids) == len(set(track_ids))

    def test_track_count_limited_by_time(self):
        """セット時間から曲数が計算される（4分/曲）"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=128, set_length_minutes=20)
        # 20分 / 4分 = 5曲
        assert result["total_tracks"] <= 5

    def test_track_count_limited_by_library(self):
        """ライブラリより多くは選ばれない"""
        small_lib = SAMPLE_TRACKS[:3]
        result = build_setlist(small_lib, start_bpm=70, set_length_minutes=120)
        assert result["total_tracks"] <= 3

    def test_direction_up_bpm_trend(self):
        """UP方向: 全体的にBPMが上がる傾向"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=70, direction=DIRECTION_UP,
                               set_length_minutes=40)
        bpms = [e["track"]["bpm"] for e in result["setlist"]]
        # 最後のBPMが最初より高い
        assert bpms[-1] >= bpms[0]

    def test_direction_down_bpm_trend(self):
        """DOWN方向: 全体的にBPMが下がる傾向"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=140, direction=DIRECTION_DOWN,
                               set_length_minutes=40)
        bpms = [e["track"]["bpm"] for e in result["setlist"]]
        # 最後のBPMが最初より低い
        assert bpms[-1] <= bpms[0]

    def test_estimated_time(self):
        """推定時間 = 曲数 × 4分"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=128, set_length_minutes=20)
        assert result["estimated_time"] == result["total_tracks"] * 4

    def test_bpm_range(self):
        """BPMレンジが1曲目と最終曲のBPMを反映"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=128)
        first_bpm = result["setlist"][0]["track"]["bpm"]
        last_bpm = result["setlist"][-1]["track"]["bpm"]
        assert result["bpm_range"]["start"] == first_bpm
        assert result["bpm_range"]["end"] == last_bpm

    def test_avg_score_range(self):
        """平均スコアが0〜100の範囲"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=128)
        assert 0 <= result["avg_score"] <= 100

    def test_max_tracks_override(self):
        """max_tracksを直接指定した場合"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=128, max_tracks=3)
        assert result["total_tracks"] <= 3


# ==============================
# format_setlist_summary テスト
# ==============================

class TestFormatSummary:

    def test_format_not_empty(self):
        """サマリーが空文字列でない"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=128, max_tracks=5)
        summary = format_setlist_summary(result)
        assert len(summary) > 0
        assert "セットリスト" in summary

    def test_format_contains_track_titles(self):
        """サマリーにトラック名が含まれる"""
        result = build_setlist(SAMPLE_TRACKS, start_bpm=128, max_tracks=3)
        summary = format_setlist_summary(result)
        first_title = result["setlist"][0]["track"]["title"]
        assert first_title in summary
