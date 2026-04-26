"""
スコアリングロジックの単体テスト（services/score.py）

BPM 最優先（weight 0.70）の設計思想に沿ったテスト構成。
"""

import pytest

from app.services.score import (
    bpm_reason,
    calc_bpm_score,
    calc_energy_score,
    calc_key_score,
    calc_total_score,
    energy_reason,
    key_reason,
    parse_camelot,
)


# ==============================
# BPMスコアテスト
# ==============================

def test_bpm_exact():
    """BPM差分0 → スコア100。"""
    score, diff = calc_bpm_score(128, 128)
    assert score == 100
    assert diff == 0


def test_bpm_small_diff():
    """BPM差分2 → スコア100（許容範囲内）。"""
    score, diff = calc_bpm_score(128, 130)
    assert score == 100
    assert diff == 2


def test_bpm_diff_3():
    """BPM差分3 → スコア90。"""
    score, diff = calc_bpm_score(128, 131)
    assert score == 90
    assert diff == 3


def test_bpm_diff_6():
    """BPM差分6 → スコア60（境界値、まだ推薦対象内）。"""
    score, diff = calc_bpm_score(128, 134)
    assert score == 60
    assert diff == 6


def test_bpm_diff_above_threshold_excluded():
    """BPM差分が 6.0 を超える → score=None（推薦から除外）。"""
    score, diff = calc_bpm_score(128, 139)
    assert score is None
    assert diff == 11


def test_bpm_diff_just_above_six_excluded():
    """BPM差分 6.5 → 除外される（しきい値 6.0 超）。"""
    score, diff = calc_bpm_score(128.0, 134.5)
    assert score is None
    assert diff == 6.5


def test_bpm_float_input_supported():
    """BPM が float でも計算できる（80.5 など）。"""
    score, diff = calc_bpm_score(80.5, 82.0)
    assert score == 100  # 差分 1.5 は ≤2 の帯域
    assert diff == 1.5


def test_bpm_float_diff_45_to_5():
    """BPM 差分 4.5 → スコア70 の帯域に入る。"""
    score, diff = calc_bpm_score(128.0, 132.5)
    assert score == 70
    assert diff == 4.5


def test_bpm_score_is_symmetric():
    """BPMスコアの計算は対称であること（base/cand を逆にしても同じ結果）。"""
    score_a, diff_a = calc_bpm_score(130, 125)
    score_b, diff_b = calc_bpm_score(125, 130)
    assert score_a == score_b
    assert diff_a == diff_b


def test_bpm_invalid_type():
    """BPM が数値でない場合は ValueError。"""
    import pytest as _pytest
    with _pytest.raises(ValueError):
        calc_bpm_score("128", 130)
    with _pytest.raises(ValueError):
        calc_bpm_score(True, 130)  # bool は弾く


# ==============================
# Keyスコアテスト（Camelot Wheel）
# ==============================

def test_key_exact():
    """完全一致 → スコア100。"""
    assert calc_key_score("8A", "8A") == 100


def test_key_neighbor_same_letter():
    """隣接番号・同Letter（8A → 9A）→ スコア95。"""
    assert calc_key_score("8A", "9A") == 95


def test_key_same_number_different_letter():
    """同Number・異Letter（8A → 8B、相対調）→ スコア90。"""
    assert calc_key_score("8A", "8B") == 90


def test_key_adjacent_different_letter():
    """隣接番号・異Letter（8A → 9B）→ スコア80。"""
    assert calc_key_score("8A", "9B") == 80


def test_key_unrelated():
    """非関連キー → スコア30。"""
    assert calc_key_score("1A", "6B") == 30


def test_key_camelot_wraparound():
    """Camelot の循環（12A → 1A は隣接）→ スコア95。"""
    assert calc_key_score("12A", "1A") == 95


def test_key_neighbor():
    """8A → 9A は隣接として評価されること（後方互換）。"""
    score = calc_key_score("8A", "9A")
    assert score >= 80


def test_parse_camelot_valid():
    """正常なCamelotキーのパース。"""
    assert parse_camelot("8A") == (8, "A")
    assert parse_camelot("12B") == (12, "B")
    assert parse_camelot("1a") == (1, "A")  # 小文字も受け付ける


def test_parse_camelot_invalid():
    """不正なCamelotキーは ValueError を送出すること。"""
    with pytest.raises(ValueError):
        parse_camelot("ZZ")
    with pytest.raises(ValueError):
        parse_camelot("0A")   # 番号は 1〜12
    with pytest.raises(ValueError):
        parse_camelot("13A")  # 番号は 1〜12
    with pytest.raises(ValueError):
        parse_camelot("8C")   # Letter は A or B のみ


# ==============================
# Energyスコアテスト
# ==============================

def test_energy_exact():
    """Energy差分0 → スコア100。"""
    assert calc_energy_score(6, 6) == 100


def test_energy_small_diff():
    """Energy差分1 → スコア95。"""
    assert calc_energy_score(5, 6) == 95


def test_energy_diff_3():
    """Energy差分3 → スコア70。"""
    assert calc_energy_score(4, 7) == 70


def test_energy_large_diff():
    """Energy差分6以上 → スコア10（最低値）。"""
    assert calc_energy_score(1, 10) == 10


def test_energy_out_of_range():
    """Energy が 1〜10 外の場合は ValueError を送出すること。"""
    with pytest.raises(ValueError):
        calc_energy_score(0, 5)
    with pytest.raises(ValueError):
        calc_energy_score(5, 11)


# ==============================
# 総合スコアテスト
# ==============================

def test_total_score_perfect_match():
    """完全一致の場合、総合スコアが100になること。"""
    base = {"bpm": 128, "key": "8A", "energy": 6}
    result = calc_total_score(base, base)
    assert result["total_score"] == 100.0


def test_total_score():
    """BPM一致・近接キーの場合、総合スコアが高くなること。"""
    base = {"bpm": 128, "key": "8A", "energy": 6}
    cand = {"bpm": 128, "key": "8A", "energy": 6}
    result = calc_total_score(base, cand)
    assert result["total_score"] >= 90


def test_total_score_bpm_weighted():
    """BPM差分が大きい候補は低スコアになること（BPM 最重視の設計確認）。"""
    base = {"bpm": 128, "key": "8A", "energy": 6}
    # BPM差6（しきい値ぎりぎり、スコア60）。Energy/Key は完全一致。
    bad_bpm = {"bpm": 134, "key": "8A", "energy": 6}
    # BPM完全一致だが、Energy と Key は離れている
    good_bpm = {"bpm": 128, "key": "1A", "energy": 1}

    result_bad = calc_total_score(base, bad_bpm)
    result_good = calc_total_score(base, good_bpm)

    # BPM一致の方が、他の指標が悪くてもスコアが高いことを確認
    assert result_bad is not None
    assert result_good is not None
    assert result_good["total_score"] > result_bad["total_score"]


def test_total_score_excluded_when_bpm_diff_too_large():
    """BPM差分が 6.0 を超える候補は None を返す（推薦から除外）。"""
    base = {"bpm": 128, "key": "8A", "energy": 6}
    far_bpm = {"bpm": 142, "key": "8A", "energy": 6}  # BPM差14
    assert calc_total_score(base, far_bpm) is None


def test_total_score_excluded_just_above_threshold():
    """BPM差分が 6.01 でも除外される（しきい値ちょうど 6.0 は許容）。"""
    base = {"bpm": 128.0, "key": "8A", "energy": 6}
    just_above = {"bpm": 134.5, "key": "8A", "energy": 6}  # 差6.5
    assert calc_total_score(base, just_above) is None


def test_total_score_with_float_bpm():
    """float BPM でも total_score を計算できる。"""
    base = {"bpm": 128.5, "key": "8A", "energy": 6}
    cand = {"bpm": 130.0, "key": "8A", "energy": 6}  # 差1.5
    result = calc_total_score(base, cand)
    assert result is not None
    assert result["total_score"] > 0


def test_total_score_returns_reason_fields():
    """calc_total_score の返り値に理由文フィールドが含まれること。"""
    base = {"bpm": 128, "key": "8A", "energy": 6}
    cand = {"bpm": 130, "key": "9A", "energy": 7}
    result = calc_total_score(base, cand)

    assert "bpm_reason" in result
    assert "energy_reason" in result
    assert "key_reason" in result
    assert isinstance(result["bpm_reason"], str)
    assert isinstance(result["energy_reason"], str)
    assert isinstance(result["key_reason"], str)


# ==============================
# 理由文テスト
# ==============================

def test_bpm_reason_exact():
    """BPM差分0〜2 → 'ほぼ一致' を含むこと。"""
    assert "ほぼ一致" in bpm_reason(0)
    assert "ほぼ一致" in bpm_reason(2)


def test_bpm_reason_moderate():
    """BPM差分3〜5 → '許容範囲' を含むこと。"""
    assert "許容範囲" in bpm_reason(3)
    assert "許容範囲" in bpm_reason(5)


def test_bpm_reason_far():
    """BPM差分が 6.0 を超える → '推薦対象外' を含むこと。"""
    assert "推薦対象外" in bpm_reason(9)


def test_bpm_reason_borderline_six():
    """BPM差分が 5 < diff <= 6 → 'やや離れている' 帯域。"""
    assert "やや離れている" in bpm_reason(6)
    assert "やや離れている" in bpm_reason(5.5)


def test_bpm_reason_float_format():
    """float の差分は小数1桁で表示される。"""
    assert "差分1.5" in bpm_reason(1.5)
    assert "差分3" in bpm_reason(3.0)  # 整数値の float は整数表示


def test_energy_reason_exact():
    """Energy差分0 → '完全一致' を含むこと。"""
    assert "完全一致" in energy_reason(0)


def test_key_reason_perfect():
    """Keyスコア100 → '完全一致' を含むこと。"""
    assert "完全一致" in key_reason(100)


def test_key_reason_unrelated():
    """Keyスコア30 → '非関連キー' を含むこと。"""
    assert "非関連キー" in key_reason(30)
