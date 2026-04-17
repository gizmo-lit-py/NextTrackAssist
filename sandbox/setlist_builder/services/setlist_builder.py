"""
セットリストビルダー
====================
開始BPM・セットの長さ・BPMの方向を指定して、
ユーザーのトラックライブラリから最適なセットリストを自動生成する。

既存の score.py のスコアリングロジックを再利用し、
1曲ずつチェーンしてセット全体を構築する。
"""

# 同ディレクトリの score.py（本体からコピー）を使う
from .score import (
    calc_bpm_score,
    calc_energy_score,
    calc_key_score,
    DEFAULT_WEIGHTS,
)


# ==============================
# 定数
# ==============================

# 1曲あたりの平均時間（分）- セット時間 → 曲数の変換に使用
AVG_TRACK_MINUTES = 4

# BPM方向ごとのボーナス/ペナルティ
DIRECTION_BONUS = 15      # 希望方向に進んだときのボーナス
DIRECTION_PENALTY = -20   # 逆方向に進んだときのペナルティ

# BPMの方向オプション
DIRECTION_UP = "up"        # 徐々に上げる
DIRECTION_KEEP = "keep"    # キープ
DIRECTION_DOWN = "down"    # 徐々に下げる


# ==============================
# BPM方向スコア
# ==============================

def calc_direction_score(current_bpm: int, candidate_bpm: int, direction: str) -> int:
    """
    BPMの方向性に対するボーナス/ペナルティを計算する。

    Args:
        current_bpm:   現在のBPM
        candidate_bpm: 候補曲のBPM
        direction:     "up" / "keep" / "down"

    Returns:
        ボーナス値（正 or 負 or 0）
    """
    diff = candidate_bpm - current_bpm

    if direction == DIRECTION_UP:
        if diff > 0:
            return DIRECTION_BONUS
        elif diff < -2:
            return DIRECTION_PENALTY
        return 0

    elif direction == DIRECTION_DOWN:
        if diff < 0:
            return DIRECTION_BONUS
        elif diff > 2:
            return DIRECTION_PENALTY
        return 0

    else:  # keep
        if abs(diff) <= 2:
            return DIRECTION_BONUS
        elif abs(diff) >= 6:
            return DIRECTION_PENALTY
        return 0


# ==============================
# セットリスト生成
# ==============================

def calc_setlist_score(current_track: dict, candidate: dict,
                       direction: str,
                       weights: dict = DEFAULT_WEIGHTS) -> dict:
    """
    セットリスト用の拡張スコアを計算する。
    通常のスコア + BPM方向ボーナスを加算。
    """
    bpm_score, bpm_diff = calc_bpm_score(current_track["bpm"], candidate["bpm"])
    energy_score = calc_energy_score(current_track["energy"], candidate["energy"])
    key_score = calc_key_score(current_track["key"], candidate["key"])

    base_total = (
        bpm_score * weights.get("bpm", 0.70)
        + energy_score * weights.get("energy", 0.20)
        + key_score * weights.get("key", 0.10)
    )

    direction_bonus = calc_direction_score(
        current_track["bpm"], candidate["bpm"], direction
    )

    # 最終スコア（0〜100にクランプ）
    final_score = max(0, min(100, base_total + direction_bonus))

    return {
        "total_score": round(final_score, 2),
        "base_score": round(base_total, 2),
        "direction_bonus": direction_bonus,
        "bpm_score": bpm_score,
        "bpm_diff": bpm_diff,
        "energy_score": energy_score,
        "key_score": key_score,
    }


def build_setlist(
    tracks: list[dict],
    start_bpm: int,
    direction: str = DIRECTION_KEEP,
    set_length_minutes: int = 60,
    max_tracks: int | None = None,
    weights: dict = DEFAULT_WEIGHTS,
) -> dict:
    """
    セットリストを自動生成する。

    Args:
        tracks:             ユーザーのトラックライブラリ
                            各トラック: {"id", "title", "artist", "bpm", "key", "energy"}
        start_bpm:          開始BPM
        direction:          BPMの方向 ("up" / "keep" / "down")
        set_length_minutes: セットの長さ（分）
        max_tracks:         最大曲数（Noneなら時間から自動計算）
        weights:            スコアリング重み

    Returns:
        {
            "setlist":       [{"track": {...}, "score_detail": {...}, "order": 1}, ...],
            "total_tracks":  セットの曲数,
            "estimated_time": 推定時間（分）,
            "bpm_range":     {"start": 開始BPM, "end": 最終BPM},
            "avg_score":     平均スコア,
        }
    """
    if not tracks:
        return {
            "setlist": [],
            "total_tracks": 0,
            "estimated_time": 0,
            "bpm_range": {"start": start_bpm, "end": start_bpm},
            "avg_score": 0,
        }

    # セット曲数を決定
    target_count = max_tracks or (set_length_minutes // AVG_TRACK_MINUTES)
    target_count = min(target_count, len(tracks))  # ライブラリより多くは選べない

    # --- 1曲目を選ぶ: 開始BPMに最も近い曲 ---
    available = list(tracks)  # コピーして使い回す
    available.sort(key=lambda t: abs(t["bpm"] - start_bpm))
    first_track = available[0]
    available.remove(first_track)

    setlist = [{
        "track": first_track,
        "score_detail": {
            "total_score": 100,
            "base_score": 100,
            "direction_bonus": 0,
            "bpm_score": 100,
            "bpm_diff": 0,
            "energy_score": 100,
            "key_score": 100,
        },
        "order": 1,
    }]

    # --- 2曲目以降: 貪欲法でスコア最大の曲を選び続ける ---
    current = first_track

    for i in range(2, target_count + 1):
        if not available:
            break

        best_candidate = None
        best_score_detail = None
        best_total = -1

        for candidate in available:
            score_detail = calc_setlist_score(
                current, candidate, direction, weights
            )
            if score_detail["total_score"] > best_total:
                best_total = score_detail["total_score"]
                best_candidate = candidate
                best_score_detail = score_detail

        if best_candidate is None:
            break

        setlist.append({
            "track": best_candidate,
            "score_detail": best_score_detail,
            "order": i,
        })

        available.remove(best_candidate)
        current = best_candidate

    # --- 統計情報 ---
    scores = [entry["score_detail"]["total_score"] for entry in setlist[1:]]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0

    return {
        "setlist": setlist,
        "total_tracks": len(setlist),
        "estimated_time": len(setlist) * AVG_TRACK_MINUTES,
        "bpm_range": {
            "start": setlist[0]["track"]["bpm"],
            "end": setlist[-1]["track"]["bpm"],
        },
        "avg_score": avg_score,
    }


# ==============================
# セットリスト表示用ヘルパー
# ==============================

def format_setlist_summary(result: dict) -> str:
    """
    セットリスト結果を人間が読める形式で返す（デバッグ・CLI用）。
    """
    lines = []
    lines.append("=" * 60)
    lines.append("  セットリスト")
    lines.append(f"  曲数: {result['total_tracks']}曲"
                 f" ｜ 推定時間: {result['estimated_time']}分")
    lines.append(f"  BPM: {result['bpm_range']['start']}"
                 f" → {result['bpm_range']['end']}")
    lines.append(f"  平均スコア: {result['avg_score']}")
    lines.append("=" * 60)

    for entry in result["setlist"]:
        t = entry["track"]
        sd = entry["score_detail"]
        order = entry["order"]

        lines.append(
            f"  #{order:02d}  {t['title']} - {t['artist']}"
            f"  [BPM:{t['bpm']} / Key:{t['key']} / Energy:{t['energy']}]"
        )
        if order > 1:
            lines.append(
                f"        スコア: {sd['total_score']}"
                f"  (BPM差:{sd['bpm_diff']}, 方向ボーナス:{sd['direction_bonus']})"
            )
        lines.append("")

    return "\n".join(lines)
