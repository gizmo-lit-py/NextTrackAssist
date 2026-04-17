# ==========================================
# NextTrackAssist - Score Engine (Final)
# ==========================================


# ==============================
# 定数（デフォルト重み）
# ==============================

DEFAULT_WEIGHTS = {
    "bpm": 0.70,
    "energy": 0.20,
    "key": 0.10
}


# ==============================
# BPMスコア
# ==============================

def calc_bpm_score(base_bpm: int, cand_bpm: int):
    if not isinstance(base_bpm, int) or not isinstance(cand_bpm, int):
        raise ValueError("BPM must be integer")

    diff = abs(base_bpm - cand_bpm)

    if diff <= 2:
        score = 100
    elif diff == 3:
        score = 90
    elif diff == 4:
        score = 80
    elif diff == 5:
        score = 70
    elif diff == 6:
        score = 60
    elif diff == 7:
        score = 40
    elif diff == 8:
        score = 20
    elif diff == 9:
        score = 5
    else:
        score = 0

    return score, diff


# ==============================
# Energyスコア
# ==============================

def calc_energy_score(base_energy: int, cand_energy: int):
    if not isinstance(base_energy, int) or not isinstance(cand_energy, int):
        raise ValueError("Energy must be integer")

    if not (1 <= base_energy <= 10 and 1 <= cand_energy <= 10):
        raise ValueError("Energy must be between 1 and 10")

    diff = abs(base_energy - cand_energy)

    if diff == 0:
        score = 100
    elif diff == 1:
        score = 95
    elif diff == 2:
        score = 85
    elif diff == 3:
        score = 70
    elif diff == 4:
        score = 50
    elif diff == 5:
        score = 30
    else:
        score = 10

    return score


# ==============================
# Camelotキー処理
# ==============================

def parse_camelot(key: str):
    if not isinstance(key, str):
        raise ValueError("Camelot key must be string")

    key = key.strip().upper()

    if len(key) < 2:
        raise ValueError("Invalid Camelot key format")

    number_part = key[:-1]
    letter_part = key[-1]

    if not number_part.isdigit():
        raise ValueError("Camelot number must be numeric")

    number = int(number_part)

    if number < 1 or number > 12:
        raise ValueError("Camelot number must be between 1 and 12")

    if letter_part not in ("A", "B"):
        raise ValueError("Camelot letter must be A or B")

    return number, letter_part


def is_adjacent(n1: int, n2: int):
    # ±1循環（12→1含む）
    return (n1 - n2) % 12 in (1, 11)


def calc_key_score(base_key: str, cand_key: str):
    n1, l1 = parse_camelot(base_key)
    n2, l2 = parse_camelot(cand_key)

    if n1 == n2 and l1 == l2:
        return 100

    if l1 == l2 and is_adjacent(n1, n2):
        return 95

    if n1 == n2 and l1 != l2:
        return 90

    if l1 != l2 and is_adjacent(n1, n2):
        return 80

    return 30


# ==============================
# 理由文
# ==============================

def bpm_reason(diff: int) -> str:
    """BPM差分から日本語の評価文を返す。"""
    if diff <= 2:
        return f"差分{diff} → ほぼ一致（ロングミックス向き）"
    elif diff <= 5:
        return f"差分{diff} → 許容範囲（軽いピッチ調整で対応可）"
    elif diff <= 8:
        return f"差分{diff} → やや離れている（ブレイク・カットイン推奨）"
    else:
        return f"差分{diff} → 大きくズレている（テンポチェンジ向き）"


def energy_reason(diff: int) -> str:
    """Energy差分から日本語の評価文を返す。"""
    if diff == 0:
        return "差分0 → 完全一致（エネルギー維持）"
    elif diff <= 2:
        return f"差分{diff} → 自然なエネルギー変化"
    elif diff <= 4:
        return f"差分{diff} → やや変化あり（意図的な緩急向き）"
    else:
        return f"差分{diff} → 乖離が大きい（セット構成を意識して）"


def key_reason(score: int) -> str:
    """Keyスコアから日本語の評価文を返す。"""
    if score == 100:
        return "完全一致（最も調和的）"
    elif score >= 95:
        return "隣接キー・同Letter（自然な転調）"
    elif score >= 90:
        return "同Number・相対調（調和が取れる）"
    elif score >= 80:
        return "隣接キー・異Letter（概ね問題なし）"
    else:
        return "非関連キー（キーの違いに注意）"


# ==============================
# 総合スコア
# ==============================

def calc_total_score(base: dict, cand: dict, weights: dict = DEFAULT_WEIGHTS):

    required_fields = ["bpm", "energy", "key"]

    for field in required_fields:
        if field not in base or field not in cand:
            raise ValueError(f"Missing required field: {field}")

    bpm_score, bpm_diff = calc_bpm_score(base["bpm"], cand["bpm"])
    energy_score = calc_energy_score(base["energy"], cand["energy"])
    key_score = calc_key_score(base["key"], cand["key"])

    bpm_w = weights.get("bpm", DEFAULT_WEIGHTS["bpm"])
    energy_w = weights.get("energy", DEFAULT_WEIGHTS["energy"])
    key_w = weights.get("key", DEFAULT_WEIGHTS["key"])

    if round(bpm_w + energy_w + key_w, 5) != 1.0:
        raise ValueError("Weights must sum to 1.0")

    total = (
        bpm_score * bpm_w +
        energy_score * energy_w +
        key_score * key_w
    )

    return {
        "bpm_diff": bpm_diff,
        "bpm_score": bpm_score,
        "energy_score": energy_score,
        "key_score": key_score,
        "total_score": round(total, 2),
        # 各軸の理由文（テンプレートで表示する）
        "bpm_reason": bpm_reason(bpm_diff),
        "energy_reason": energy_reason(abs(base["energy"] - cand["energy"])),
        "key_reason": key_reason(key_score),
    }


# ==============================
# 単体テスト用
# ==============================

if __name__ == "__main__":
    base_track = {
        "bpm": 140,
        "energy": 8,
        "key": "8A"
    }

    candidate = {
        "bpm": 146,
        "energy": 7,
        "key": "9A"
    }

    print(calc_total_score(base_track, candidate))