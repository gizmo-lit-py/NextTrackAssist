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

# BPM差がこの値より大きい候補は推薦から除外する。
# （6.0 ちょうどは含む / 6.0001 以上は除外）
BPM_EXCLUSION_THRESHOLD = 6.0


# ==============================
# BPMスコア
# ==============================

def calc_bpm_score(base_bpm, cand_bpm):
    """
    BPMの近さからスコアを返す。

    Returns:
        (score, diff)
        - score: 0〜100 の整数。
                 BPM差が BPM_EXCLUSION_THRESHOLD（6.0）を超える場合は None。
        - diff:  abs(base - cand) を float で返す（整数BPMでも float）。
    """
    if not isinstance(base_bpm, (int, float)) or isinstance(base_bpm, bool):
        raise ValueError("BPM must be a number (int or float)")
    if not isinstance(cand_bpm, (int, float)) or isinstance(cand_bpm, bool):
        raise ValueError("BPM must be a number (int or float)")

    diff = abs(float(base_bpm) - float(cand_bpm))

    # 6.0 を超えたら推薦から除外（None を返す）
    if diff > BPM_EXCLUSION_THRESHOLD:
        return None, diff

    # 既存のスコア帯を float 対応の閾値ベースに置き換え
    if diff <= 2.0:
        score = 100
    elif diff <= 3.0:
        score = 90
    elif diff <= 4.0:
        score = 80
    elif diff <= 5.0:
        score = 70
    else:  # 5.0 < diff <= 6.0
        score = 60

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

def _format_diff(diff) -> str:
    """整数値ならそのまま、小数なら小数第1位まで表示する。"""
    if isinstance(diff, (int, float)) and float(diff).is_integer():
        return str(int(diff))
    return f"{diff:.1f}"


def bpm_reason(diff) -> str:
    """BPM差分から日本語の評価文を返す。int / float 両対応。"""
    d = float(diff)
    label = _format_diff(diff)
    if d <= 2.0:
        return f"差分{label} → ほぼ一致（ロングミックス向き）"
    elif d <= 5.0:
        return f"差分{label} → 許容範囲（軽いピッチ調整で対応可）"
    elif d <= BPM_EXCLUSION_THRESHOLD:
        return f"差分{label} → やや離れている（ブレイク・カットイン推奨）"
    else:
        return f"差分{label} → BPM差が大きすぎるため推薦対象外"


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
    """
    総合スコアを計算する。

    BPM差が BPM_EXCLUSION_THRESHOLD（6.0）を超える場合は
    推薦対象外とみなし、None を返す。呼び出し側でフィルタすること。
    """

    required_fields = ["bpm", "energy", "key"]

    for field in required_fields:
        if field not in base or field not in cand:
            raise ValueError(f"Missing required field: {field}")

    bpm_score, bpm_diff = calc_bpm_score(base["bpm"], cand["bpm"])

    # BPM差が大きすぎる候補は推薦対象外
    if bpm_score is None:
        return None

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