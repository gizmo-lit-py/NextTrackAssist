"""
スコアリングロジックの単体テスト（services/score.py）

BPM・Key・Energy の各スコア計算と、
BPM差が閾値を超えた場合の除外ロジックをカバーしている。
"""

from app.services.score import (
    calc_bpm_score,
    calc_energy_score,
    calc_key_score,
    calc_total_score,
)


def test_bpm_exact():
    """BPM差分0 → スコア100。"""
    score, diff = calc_bpm_score(128, 128)
    assert score == 100
    assert diff == 0


def test_key_exact():
    """Keyが完全一致 → スコア100。"""
    assert calc_key_score("8A", "8A") == 100


def test_energy_exact():
    """Energy差分0 → スコア100。"""
    assert calc_energy_score(6, 6) == 100


def test_total_score_perfect_match():
    """BPM・Key・Energy がすべて一致する場合、総合スコアが100になること。"""
    base = {"bpm": 128, "key": "8A", "energy": 6}
    result = calc_total_score(base, base)
    assert result["total_score"] == 100.0


def test_total_score_excluded_when_bpm_diff_too_large():
    """BPM差分が6を超える候補は推薦から除外され None が返ること。"""
    base = {"bpm": 128, "key": "8A", "energy": 6}
    far  = {"bpm": 142, "key": "8A", "energy": 6}
    assert calc_total_score(base, far) is None
