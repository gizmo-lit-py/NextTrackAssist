"""
rekordbox のエクスポートファイル（CSV / TSV）をパースして、
このアプリの Track モデルに変換するサービスモジュール。

rekordbox のエクスポートファイルは タブ区切り（TSV） で、
先頭行が "#" から始まる特殊なフォーマット。

例:
    #\tTrack Title\tArtist\tBPM\tMusical Key\t...
    1\tInsomnia\tFaithless\t136.0\t8A\t...
"""

import csv
import io


# ---------------------------------------------------------------------------
# Musical Key → Camelot 変換テーブル
# ---------------------------------------------------------------------------
# rekordbox の "Musical Key" 列は、ユーザー設定によって
# Camelot 形式（"8A"）の場合も、楽典記号（"Am"）の場合もある。
# 楽典記号が来た場合はこのテーブルで Camelot に変換する。

MUSICAL_KEY_TO_CAMELOT = {
    # --- Major keys（メジャー = Camelot の B サフィックス）---
    "C":    "8B",
    "G":    "9B",
    "D":    "10B",
    "A":    "11B",
    "E":    "12B",
    "B":    "1B",
    "F#":   "2B",  "Gb":  "2B",
    "Db":   "3B",  "C#":  "3B",
    "Ab":   "4B",  "G#":  "4B",
    "Eb":   "5B",  "D#":  "5B",
    "Bb":   "6B",  "A#":  "6B",
    "F":    "7B",
    # --- Minor keys（マイナー = Camelot の A サフィックス）---
    "Am":   "8A",
    "Em":   "9A",
    "Bm":   "10A",
    "F#m":  "11A", "Gbm": "11A",
    "C#m":  "12A", "Dbm": "12A",
    "G#m":  "1A",  "Abm": "1A",
    "D#m":  "2A",  "Ebm": "2A",
    "Bbm":  "3A",  "A#m": "3A",
    "Fm":   "4A",
    "Cm":   "5A",
    "Gm":   "6A",
    "Dm":   "7A",
}

# ---------------------------------------------------------------------------
# rekordbox のカラム名（バージョンや言語設定で微妙に違う場合がある）
# ---------------------------------------------------------------------------
TITLE_COLS  = {"Track Title", "曲名", "Title", "トラックタイトル"}
ARTIST_COLS = {"Artist", "アーティスト"}
BPM_COLS    = {"BPM"}
KEY_COLS    = {"Musical Key", "Key", "キー", "Tonart"}  # 英/日/独の列名

# Camelot キーとして有効な末尾文字
_CAMELOT_LETTERS = {"A", "B"}

# Energy はrekordboxに対応列がないので固定のデフォルト値を使う
DEFAULT_ENERGY = 5
MAX_FILE_SIZE  = 5 * 1024 * 1024  # 5 MB


# ---------------------------------------------------------------------------
# 内部ヘルパー関数
# ---------------------------------------------------------------------------

def _detect_encoding(raw: bytes) -> str:
    """
    ファイル先頭の BOM（バイトオーダーマーク）を見て
    文字コードを判定する。
    """
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16"         # Windows の rekordbox でよくある
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"      # UTF-8 with BOM
    return "utf-8"


def _find_col_index(header_row: list[str], candidates: set[str]) -> int | None:
    """
    ヘッダ行の中から candidates に含まれる列名を探し、インデックスを返す。
    見つからなければ None を返す。
    """
    for i, col in enumerate(header_row):
        if col.strip() in candidates:
            return i
    return None


def _is_camelot(key: str) -> bool:
    """
    文字列が Camelot 形式（例: "8A", "11B"）かどうかを簡易チェック。
    """
    key = key.strip().upper()
    if len(key) < 2:
        return False
    letter = key[-1]
    number_part = key[:-1]
    if letter not in _CAMELOT_LETTERS:
        return False
    if not number_part.isdigit():
        return False
    n = int(number_part)
    return 1 <= n <= 12


def _to_camelot(raw_key: str) -> str | None:
    """
    キー文字列を Camelot コードに変換する。

    1. すでに Camelot 形式（"8A" など）なら大文字化して返す。
    2. 楽典記号（"Am", "C#" など）なら変換テーブルで変換して返す。
    3. どちらにも当てはまらなければ None を返す。
    """
    key = raw_key.strip()
    if not key:
        return None

    if _is_camelot(key):
        return key.upper()

    # 変換テーブルで探す（まず原文、次に先頭大文字で再試行）
    camelot = MUSICAL_KEY_TO_CAMELOT.get(key)
    if camelot is None:
        # "am" → "Am" のように先頭だけ大文字にして再試行
        camelot = MUSICAL_KEY_TO_CAMELOT.get(key.capitalize())
    return camelot  # None の場合は変換失敗


# ---------------------------------------------------------------------------
# メイン公開関数
# ---------------------------------------------------------------------------

def parse_rekordbox_csv(file_bytes: bytes, default_energy: int = DEFAULT_ENERGY) -> dict:
    """
    rekordbox のエクスポートファイル（バイト列）をパースして結果を返す。

    Args:
        file_bytes:       アップロードされたファイルのバイト列
        default_energy:   Energy のデフォルト値（1〜10、デフォルトは5）

    Returns:
        {
            "tracks":       [{"title": ..., "artist": ..., "bpm": ...,
                              "key": ..., "energy": ...}, ...],
            "imported":     成功した行数,
            "skipped":      スキップした行数,
            "skip_reasons": ["行3: BPMが範囲外 (400)", ...]  # 最大20件
        }
    """
    # ---- ファイルサイズチェック ----
    if len(file_bytes) > MAX_FILE_SIZE:
        return {
            "tracks": [],
            "imported": 0,
            "skipped": 0,
            "skip_reasons": [f"ファイルサイズが上限（5MB）を超えています"],
        }

    # ---- 文字コードを判定してデコード ----
    encoding = _detect_encoding(file_bytes)
    try:
        text = file_bytes.decode(encoding, errors="replace")
    except Exception:
        text = file_bytes.decode("utf-8", errors="replace")

    # ---- タブ区切りかカンマ区切りかを自動判定 ----
    first_line = text.split("\n")[0]
    delimiter = "\t" if "\t" in first_line else ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        return {"tracks": [], "imported": 0, "skipped": 0,
                "skip_reasons": ["ファイルが空です"]}

    # ---- ヘッダ行を探す ----
    # rekordbox のエクスポートは先頭セルが "#" のヘッダ行を持つ
    header_row = None
    data_start = 0

    for i, row in enumerate(rows):
        if not row:
            continue
        first_cell = row[0].strip()
        if first_cell == "#":
            # 典型的な rekordbox ヘッダ行
            header_row = [c.strip() for c in row]
            data_start = i + 1
            break
        if first_cell in TITLE_COLS or any(c.strip() in TITLE_COLS for c in row):
            # "Track Title" などがある行
            header_row = [c.strip() for c in row]
            data_start = i + 1
            break

    if header_row is None:
        return {
            "tracks": [],
            "imported": 0,
            "skipped": max(0, len(rows) - 1),
            "skip_reasons": ["ヘッダ行が見つかりませんでした（"
                             "\"Track Title\",\"Artist\",\"BPM\" の列が必要です）"],
        }

    # ---- 各列のインデックスを特定 ----
    title_idx  = _find_col_index(header_row, TITLE_COLS)
    artist_idx = _find_col_index(header_row, ARTIST_COLS)
    bpm_idx    = _find_col_index(header_row, BPM_COLS)
    key_idx    = _find_col_index(header_row, KEY_COLS)  # None でも続行可（Keyなし扱い）

    # 必須列が見つからない場合は即終了
    if title_idx is None or artist_idx is None or bpm_idx is None:
        missing = []
        if title_idx is None:
            missing.append("Track Title")
        if artist_idx is None:
            missing.append("Artist")
        if bpm_idx is None:
            missing.append("BPM")
        return {
            "tracks": [],
            "imported": 0,
            "skipped": max(0, len(rows) - data_start),
            "skip_reasons": [f"必須列が見つかりません: {', '.join(missing)}"],
        }

    # ---- 各データ行を処理 ----
    tracks = []
    skipped = 0
    skip_reasons = []

    def get_cell(row: list[str], idx: int | None) -> str:
        """行から安全にセルの値を取得する。"""
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    for row_no, row in enumerate(rows[data_start:], start=data_start + 2):
        # 空行はスキップ（カウントしない）
        if not row or all(c.strip() == "" for c in row):
            continue

        title    = get_cell(row, title_idx)
        artist   = get_cell(row, artist_idx)
        raw_bpm  = get_cell(row, bpm_idx)
        raw_key  = get_cell(row, key_idx)

        # -- Title チェック --
        if not title:
            skipped += 1
            skip_reasons.append(f"行{row_no}: タイトルが空のためスキップ")
            continue

        # -- Artist チェック --
        if not artist:
            artist = "Unknown"

        # -- BPM 変換（"136.0" → 136）--
        try:
            bpm = int(float(raw_bpm))
        except (ValueError, TypeError):
            skipped += 1
            skip_reasons.append(f"行{row_no}: BPM '{raw_bpm}' が数値でないためスキップ")
            continue

        if not (40 <= bpm <= 250):
            skipped += 1
            skip_reasons.append(
                f"行{row_no}: BPM {bpm} が範囲外（40〜250）のためスキップ"
            )
            continue

        # -- Key 変換 --
        if raw_key:
            camelot_key = _to_camelot(raw_key)
            if camelot_key is None:
                skipped += 1
                skip_reasons.append(
                    f"行{row_no}: Key '{raw_key}' が認識できない形式のためスキップ"
                )
                continue
        else:
            # Key 列がないか空の場合はデフォルト（"8A" = Cマイナー）
            camelot_key = "8A"

        # -- Energy はデフォルト値を使用（rekordboxに対応フィールドなし）--
        tracks.append({
            "title":   title,
            "artist":  artist,
            "bpm":     bpm,
            "key":     camelot_key,
            "energy":  default_energy,
        })

    return {
        "tracks":       tracks,
        "imported":     len(tracks),
        "skipped":      skipped,
        "skip_reasons": skip_reasons[:20],  # UIに表示するのは最大20件まで
    }
