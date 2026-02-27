# ===============================
# スコア設定（変更可能エリア）
# ===============================

BPM_WEIGHTS = 0.4
KEY_WEIGHTS = 0.4
ENERGY_WEIGHTS = 0.2

KEY_LABELS = {
    100: "MATCH",
    90: "ADJ",
    85: "REL",
    40: "NG"
}


# ===============================
# BPMスコア
# ===============================

def calc_bpm_score(base_bpm, cand_bpm):

    base_bpm = int(base_bpm)
    cand_bpm = int(cand_bpm)

    diff = abs(base_bpm - cand_bpm)

    if diff <= 2:
        return 100, f"差分{diff} → ほぼ一致"
    elif diff <= 5:
        return 80, f"差分{diff} → 許容範囲"
    elif diff <= 10:
        return 50, f"差分{diff} → やや離れている"
    else:
        return 20, f"差分{diff} → 変化大"


# ===============================
# Energyスコア
# ===============================

def calc_energy_score(base_energy, cand_energy):

    base_energy = int(base_energy)
    cand_energy = int(cand_energy)

    diff = abs(base_energy - cand_energy)

    if diff <= 1:
        return 100, f"差分{diff} → 流れ維持"
    elif diff == 2:
        return 70, f"差分{diff} → やや変化"
    else:
        return 40, f"差分{diff} → 変化大"


# ===============================
# Keyスコア
# ===============================

def calc_key_score(base_key, cand_key):

    base_key = str(base_key)
    cand_key = str(cand_key)

    if base_key == cand_key:
        return 100, KEY_LABELS[100]

    base_number = int(base_key[:-1])
    base_letter = base_key[-1]

    cand_number = int(cand_key[:-1])
    cand_letter = cand_key[-1]

    is_adjacent_normal = abs(base_number - cand_number) == 1
    is_adjacent_wrap = (
        (base_number == 1 and cand_number == 12) or
        (base_number == 12 and cand_number == 1)
    )

    if base_letter == cand_letter and (is_adjacent_normal or is_adjacent_wrap):
        return 90, KEY_LABELS[90]

    if base_number == cand_number and base_letter != cand_letter:
        return 85, KEY_LABELS[85]

    return 40, KEY_LABELS[40]


# ===============================
# 総合スコア
# ===============================

def calc_total_score(bpm_score, key_score, energy_score):

    bpm_score = int(bpm_score)
    key_score = int(key_score)
    energy_score = int(energy_score)

    total = (
        bpm_score * BPM_WEIGHTS
        + key_score * KEY_WEIGHTS
        + energy_score * ENERGY_WEIGHTS
    )

    return int(total)


# ===============================
# 総合マッチ計算
# ===============================

def calculate_match_score(base_track, cand_track):

    bpm_score, bpm_reason = calc_bpm_score(
        base_track["bpm"],
        cand_track["bpm"]
    )

    key_score, key_label = calc_key_score(
        base_track["key"],
        cand_track["key"]
    )

    energy_score, energy_reason = calc_energy_score(
        base_track["energy"],
        cand_track["energy"]
    )

    total_score = calc_total_score(
        bpm_score,
        key_score,
        energy_score
    )

    return {
        "bpm_score": bpm_score,
        "bpm_reason": bpm_reason,

        "key_score": key_score,
        "key_label": key_label,

        "energy_score": energy_score,
        "energy_reason": energy_reason,

        "total_score": total_score
    }