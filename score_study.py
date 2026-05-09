# ==================================================
# score.py を一から理解するための学習ファイル
# ==================================================
# このファイルは「写経しながら理解する」用。
# コメントを読みながら自分で書いてみてください。
# ==================================================


# ==============================
# STEP 1: 定数（じょうすう）を定義する
# ==============================
#
# 「定数」とは = 変わらない固定値のこと。
# 変数は変わるもの、定数は変わらないもの。
#
# ここでは「BPM・Energy・Keyのスコアに何%の重みをかけるか」を定義する。
#
# dict（辞書型） = { キー: 値 } の形でデータをセットで管理できる型
#   例: person = {"name": "太郎", "age": 25}
#       → person["name"] で "太郎" が取れる
#
# なぜBPMが70%？
#   → BPMがズレると即座にミックスが崩れる。一番重要だから。

DEFAULT_WEIGHTS = {
    "bpm": 0.70,      # BPMの重み：70%
    "energy": 0.20,   # Energyの重み：20%
    "key": 0.10       # Keyの重み：10%
}


# ==============================
# STEP 2: BPMスコアを計算する関数
# ==============================
#
# 「関数（function）」とは = 処理をひとまとめにして名前をつけたもの。
#   def 関数名(引数1, 引数2): の形で定義する
#
# 「引数（ひきすう）」とは = 関数に渡すデータのこと。
#   ここでは base_bpm（今流してる曲のBPM）と cand_bpm（候補曲のBPM）を渡す。
#
# 「: int」とは = 型ヒント。「この引数はintを期待してるよ」という印。
#   Pythonは実際には型チェックしてくれないけど、読みやすくなる。
#
# 「abs()」とは = absolute（絶対値）の略。
#   abs(-5) → 5、abs(3) → 3  ← マイナスを消す関数
#   BPMの差がプラスかマイナスかは関係ないので絶対値を使う。
#
# 「isinstance(値, 型)」とは = 「この値はこの型ですか？」を確認する関数。
#   isinstance(130, int) → True
#   isinstance("130", int) → False（文字列なのでFalse）
#
# 「raise ValueError("...")」とは = エラーを意図的に発生させること。
#   おかしなデータが来たときに「ここがおかしいよ」と教える仕組み。

def calc_bpm_score(base_bpm: int, cand_bpm: int):

    # まず「ちゃんとintが来てるか」チェック（バリデーション）
    if not isinstance(base_bpm, int) or not isinstance(cand_bpm, int):
        raise ValueError("BPM must be integer")

    # BPMの差を計算（マイナスにならないよう絶対値を使う）
    diff = abs(base_bpm - cand_bpm)

    # diffの値によってスコアを決める（if-elif-elseで分岐）
    # 差が小さいほど高スコア = 相性が良い
    if diff <= 2:
        score = 100    # ほぼ同じBPM → 最高
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
        score = 0      # 差が10以上 → 使えない

    # 「return」とは = 関数の結果として値を返すこと。
    # ここでは score と diff の2つを返している（タプルという形式）
    return score, diff


# ==============================
# STEP 3: Energyスコアを計算する関数
# ==============================
#
# Energyとは = 曲の盛り上がり度（1〜10の整数）
# 差が小さい = エネルギーの流れが自然 → 高スコア
#
# 「1 <= base_energy <= 10」とは = 数学と同じ不等式チェック。
#   Pythonでは a <= x <= b という書き方ができる（他の言語ではできないことも多い）

def calc_energy_score(base_energy: int, cand_energy: int):

    if not isinstance(base_energy, int) or not isinstance(cand_energy, int):
        raise ValueError("Energy must be integer")

    # Energyは1〜10の範囲でないといけない
    if not (1 <= base_energy <= 10 and 1 <= cand_energy <= 10):
        raise ValueError("Energy must be between 1 and 10")

    diff = abs(base_energy - cand_energy)

    if diff == 0:
        score = 100   # 完全一致
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
        score = 10    # 差が6以上

    # Energyは score だけ返す（diffは外で計算できる）
    return score


# ==============================
# STEP 4: Camelot Wheelのキー処理
# ==============================
#
# Camelot Wheel（ケイメロットホイール）とは？
#   → DJが使うキー（調）の互換性を表した12点の円形チャート。
#   → 「8A」「9B」のような「数字＋A or B」で表す。
#     数字：1〜12（音楽の12の調に対応）
#     A：マイナー系、B：メジャー系
#   → 隣り合うキーは相性が良い（自然な転調ができる）
#
# parse_camelot（パース＝文字列を解析する）
#   "8A" → (8, "A") という数字と文字に分解する関数
#
# 「key[:-1]」とは = 文字列の最後の1文字以外を取得
#   "8A"[:-1] → "8"
#   "12B"[:-1] → "12"
#
# 「key[-1]」とは = 文字列の最後の1文字を取得
#   "8A"[-1] → "A"
#
# 「.strip()」とは = 前後の空白を取り除く
#   "  8A  ".strip() → "8A"
#
# 「.upper()」とは = 大文字に変換する
#   "8a".upper() → "8A"
#
# 「.isdigit()」とは = 「全部数字ですか？」を確認
#   "8".isdigit() → True
#   "8A".isdigit() → False

def parse_camelot(key: str):

    if not isinstance(key, str):
        raise ValueError("Camelot key must be string")

    key = key.strip().upper()   # 前後の空白を取って大文字にする

    if len(key) < 2:
        raise ValueError("Invalid Camelot key format")

    number_part = key[:-1]   # 最後の文字以外（数字部分）
    letter_part = key[-1]    # 最後の文字（AかB）

    if not number_part.isdigit():
        raise ValueError("Camelot number must be numeric")

    number = int(number_part)  # "8" → 8（文字列→整数に変換）

    if number < 1 or number > 12:
        raise ValueError("Camelot number must be between 1 and 12")

    if letter_part not in ("A", "B"):
        raise ValueError("Camelot letter must be A or B")

    return number, letter_part  # 例: "8A" → (8, "A")


# ==============================
# STEP 5: 「隣接してるか」チェックする関数
# ==============================
#
# Camelot Wheelは12が最大で、次は1に戻る「円形」。
#   → 12と1は隣接している！（12→1→2→...→12と循環する）
#
# 「% 12」とは = 12で割ったあまり（剰余/モジュロ演算）
#   13 % 12 → 1
#   0 % 12 → 0
#
# なぜ (n1 - n2) % 12 in (1, 11) ？
#   差が1 = 1つ隣（例：8→9）
#   差が11 = もう一方向で1つ隣（例：1→12 は 1-12=-11 → -11%12=1）
#   ※Pythonの % はマイナスでも正の数を返す特徴がある

def is_adjacent(n1: int, n2: int):
    return (n1 - n2) % 12 in (1, 11)


# ==============================
# STEP 6: キースコアを計算する関数
# ==============================
#
# Camelot Wheelでの相性：
#   完全一致（例: 8A → 8A）　　→ 100点
#   隣接・同Letter（例: 8A → 9A）→ 95点（自然な転調）
#   同Number・相対調（例: 8A → 8B）→ 90点（メジャー↔マイナー）
#   隣接・異Letter（例: 8A → 9B）→ 80点（少し工夫が必要）
#   それ以外　　　　　　　　　　→ 30点（相性が悪い）

def calc_key_score(base_key: str, cand_key: str):

    n1, l1 = parse_camelot(base_key)   # base_keyを数字と文字に分解
    n2, l2 = parse_camelot(cand_key)   # cand_keyを数字と文字に分解

    # 完全一致
    if n1 == n2 and l1 == l2:
        return 100

    # 隣接・同Letter（例: 8A→9A）
    if l1 == l2 and is_adjacent(n1, n2):
        return 95

    # 同Number・相対調（例: 8A→8B）
    if n1 == n2 and l1 != l2:
        return 90

    # 隣接・異Letter（例: 8A→9B）
    if l1 != l2 and is_adjacent(n1, n2):
        return 80

    # それ以外
    return 30


# ==============================
# STEP 7: 理由文（UI表示用のテキスト）
# ==============================
#
# 「-> str」とは = 「この関数はstr（文字列）を返しますよ」という型ヒント
#
# f文字列とは = f"..." の形で変数を文字列に埋め込める書き方
#   diff = 3 のとき、f"差分{diff}" → "差分3"

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
# STEP 8: 総合スコアをまとめる関数（メインの関数）
# ==============================
#
# これが一番大事な関数。BPM・Energy・Keyのスコアを合算して返す。
#
# 「引数のデフォルト値」とは = weights=DEFAULT_WEIGHTS のように
#   呼び出すとき weights を省略したら DEFAULT_WEIGHTS が使われる。
#
# 「weights.get("bpm", DEFAULT_WEIGHTS["bpm"])」とは？
#   → weights辞書から "bpm" キーの値を取得する。
#   → 万が一 "bpm" キーがなかったら DEFAULT_WEIGHTS["bpm"] を使う（安全策）
#
# 「round(数値, 小数点以下の桁数)」とは = 四捨五入する関数
#   round(92.567, 2) → 92.57

def calc_total_score(base: dict, cand: dict, weights: dict = DEFAULT_WEIGHTS):

    # まず必要なフィールドが揃ってるかチェック
    required_fields = ["bpm", "energy", "key"]

    for field in required_fields:
        if field not in base or field not in cand:
            raise ValueError(f"Missing required field: {field}")

    # 各スコアを計算
    bpm_score, bpm_diff = calc_bpm_score(base["bpm"], cand["bpm"])
    energy_score = calc_energy_score(base["energy"], cand["energy"])
    key_score = calc_key_score(base["key"], cand["key"])

    # 重みを取得
    bpm_w = weights.get("bpm", DEFAULT_WEIGHTS["bpm"])
    energy_w = weights.get("energy", DEFAULT_WEIGHTS["energy"])
    key_w = weights.get("key", DEFAULT_WEIGHTS["key"])

    # 重みの合計が1.0でないとおかしいのでチェック
    # round(値, 5) → 浮動小数点の誤差を吸収するため小数5桁で丸める
    if round(bpm_w + energy_w + key_w, 5) != 1.0:
        raise ValueError("Weights must sum to 1.0")

    # 重み付き合計スコアを計算
    total = (
        bpm_score * bpm_w +       # 例: 100 × 0.70 = 70.0
        energy_score * energy_w + # 例: 95  × 0.20 = 19.0
        key_score * key_w         # 例: 80  × 0.10 =  8.0
    )                             #              合計 = 97.0

    # 辞書（dict）にまとめて返す
    return {
        "bpm_diff": bpm_diff,
        "bpm_score": bpm_score,
        "energy_score": energy_score,
        "key_score": key_score,
        "total_score": round(total, 2),
        "bpm_reason": bpm_reason(bpm_diff),
        "energy_reason": energy_reason(abs(base["energy"] - cand["energy"])),
        "key_reason": key_reason(key_score),
    }


# ==============================
# STEP 9: このファイル単体でテスト実行する
# ==============================
#
# 「if __name__ == "__main__":」とは？
#   → このファイルを直接 python score.py として実行したときだけ動くブロック。
#   → 他のファイルから import されたときは動かない。
#   → 「単体テスト」や「動作確認」に使う定番の書き方。
#
# 試し方：VSCodeのターミナルで
#   python score_study.py
# と打つと下の結果が出る。

if __name__ == "__main__":
    base_track = {
        "bpm": 140,
        "energy": 8,
        "key": "8A"
    }

    candidate = {
        "bpm": 146,     # BPM差 = 6 → score=60
        "energy": 7,    # Energy差 = 1 → score=95
        "key": "9A"     # 隣接・同Letter → score=95
    }

    result = calc_total_score(base_track, candidate)
    print(result)

    # 期待される出力：
    # total_score = 60×0.70 + 95×0.20 + 95×0.10 = 42 + 19 + 9.5 = 70.5
