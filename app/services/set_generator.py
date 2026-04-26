# ==========================================
# NextTrackAssist - DJ Set Generator
# ==========================================
#
# DJセットを自動生成するサービス。
# score.py の calc_total_score を繰り返し呼び、
# BPMカーブ（開始→目標）を滑らかにつなぐ最適セットを組む。
# ==========================================

from app.models.track import Track
from app.services.score import calc_total_score


# ==============================
# BPMカーブ制御
# ==============================

def _expected_bpm(current_bpm, target_bpm, remaining_steps: int) -> float:
    """
    残りステップ数に応じて「次の曲で期待されるBPM」を計算。
    BPM は int / float どちらでも受け付ける。
    例: current=126, target=134, remaining=4
        → 126 + (134-126)/4 = 128.0
    """
    if remaining_steps <= 0:
        return float(target_bpm)
    return float(current_bpm) + (float(target_bpm) - float(current_bpm)) / remaining_steps


def _bpm_curve_penalty(cand_bpm, expected_bpm: float) -> float:
    """
    候補曲のBPMが期待BPMからズレている場合のペナルティ（0〜30点）。
    ズレが大きいほど total_score から減算される。BPM は int / float 両対応。
    """
    diff = abs(float(cand_bpm) - float(expected_bpm))
    return min(diff * 3, 30)


# ==============================
# セット生成メイン
# ==============================

def generate_dj_set(
    db,
    user_id: int,
    start_bpm,
    target_bpm,
    num_tracks: int,
) -> dict:
    """
    DJセットを自動生成する。

    Args:
        db:          SQLAlchemy セッション
        user_id:     ログインユーザーID
        start_bpm:   セット開始時のBPM（例: 124）
        target_bpm:  セット終了時の目標BPM（例: 134）
        num_tracks:  セットに含める曲数（2〜30）

    Returns:
        {
            "tracks": [
                {"id", "title", "artist", "bpm", "key", "energy",
                 "score", "bpm_reason", "energy_reason", "key_reason"},
                ...
            ],
            "bpm_curve":    [126, 128, 130, ...],
            "energy_curve": [6, 7, 7, 8, ...],
            "avg_score":    87.3,
            "total_tracks": 10,
        }

    Raises:
        ValueError: num_tracks < 2 またはライブラリ不足
    """

    # ---- バリデーション ----
    if num_tracks < 2:
        raise ValueError("num_tracks must be at least 2")
    if not (40 <= start_bpm <= 250):
        raise ValueError("start_bpm must be between 40 and 250")
    if not (40 <= target_bpm <= 250):
        raise ValueError("target_bpm must be between 40 and 250")

    # ---- ユーザーの全トラックを取得 ----
    pool = db.query(Track).filter(Track.user_id == user_id).all()

    if len(pool) < num_tracks:
        raise ValueError(
            f"Not enough tracks in library. "
            f"Need {num_tracks}, have {len(pool)}."
        )

    # ---- 開始曲を選ぶ: start_bpm に最も近い曲 ----
    first = min(pool, key=lambda t: abs(float(t.bpm) - float(start_bpm)))
    selected = [first]
    used_ids = {first.id}
    scores = []

    # ---- 貪欲法でセットを構築 ----
    for step in range(1, num_tracks):
        current = selected[-1]
        remaining = num_tracks - step
        expected = _expected_bpm(current.bpm, target_bpm, remaining)

        base_payload = {
            "bpm": current.bpm,
            "energy": current.energy,
            "key": current.key,
        }

        best_cand = None
        best_adjusted = -1
        best_result = None

        for cand in pool:
            if cand.id in used_ids:
                continue

            result = calc_total_score(
                base_payload,
                {"bpm": cand.bpm, "energy": cand.energy, "key": cand.key},
            )

            # BPM差が大きすぎる候補（result is None）はセット候補から除外
            if result is None:
                continue

            # BPMカーブへの追従ボーナス/ペナルティ
            penalty = _bpm_curve_penalty(cand.bpm, expected)
            adjusted = result["total_score"] - penalty

            if adjusted > best_adjusted:
                best_adjusted = adjusted
                best_cand = cand
                best_result = result

        if best_cand is None:
            # BPM差6以下の候補が尽きたらセット構築を打ち切る
            break

        selected.append(best_cand)
        used_ids.add(best_cand.id)
        scores.append(best_result)

    # ---- 結果を組み立て ----
    track_list = []
    for i, track in enumerate(selected):
        entry = {
            "id": track.id,
            "title": track.title,
            "artist": track.artist,
            "bpm": track.bpm,
            "key": track.key,
            "energy": track.energy,
        }
        if i > 0 and i - 1 < len(scores):
            r = scores[i - 1]
            entry.update({
                "score": r["total_score"],
                "bpm_reason": r["bpm_reason"],
                "energy_reason": r["energy_reason"],
                "key_reason": r["key_reason"],
            })
        track_list.append(entry)

    avg_score = (
        round(sum(r["total_score"] for r in scores) / len(scores), 2)
        if scores else 0
    )

    return {
        "tracks": track_list,
        "bpm_curve": [t.bpm for t in selected],
        "energy_curve": [t.energy for t in selected],
        "avg_score": avg_score,
        "total_tracks": len(selected),
    }
