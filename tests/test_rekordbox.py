"""
rekordbox CSV パーサーの単体テスト。

テストの方針:
  - DB やルートを使わず、parse_rekordbox_csv() だけをテストする（純粋な単体テスト）
  - 正常系・異常系・エッジケースをすべてカバーする
"""

import pytest
from app.services.rekordbox import (
    parse_rekordbox_csv,
    _is_camelot,
    _to_camelot,
    MAX_FILE_SIZE,
)


# ===========================================================================
# ヘルパー関数: テスト用 CSV バイト列を生成する
# ===========================================================================

def make_tsv(*rows: str) -> bytes:
    """
    タブ区切りの行リストを UTF-8 バイト列に変換する。
    先頭行に rekordbox 標準ヘッダを自動付与する。
    """
    header = "#\tTrack Title\tArtist\tBPM\tMusical Key"
    lines = [header] + list(rows)
    return "\n".join(lines).encode("utf-8")


# ===========================================================================
# 内部ヘルパー関数のテスト
# ===========================================================================

class TestIsCamelot:
    def test_valid_camelot_a(self):
        assert _is_camelot("8A") is True

    def test_valid_camelot_b(self):
        assert _is_camelot("11B") is True

    def test_boundary_1a(self):
        assert _is_camelot("1A") is True

    def test_boundary_12b(self):
        assert _is_camelot("12B") is True

    def test_lowercase_is_valid(self):
        # _is_camelot は大文字化して判定する
        assert _is_camelot("8a") is True

    def test_invalid_letter_c(self):
        assert _is_camelot("8C") is False

    def test_invalid_number_0(self):
        assert _is_camelot("0A") is False

    def test_invalid_number_13(self):
        assert _is_camelot("13A") is False

    def test_musical_key_am(self):
        assert _is_camelot("Am") is False

    def test_empty_string(self):
        assert _is_camelot("") is False


class TestToCamelot:
    def test_already_camelot_uppercase(self):
        assert _to_camelot("8A") == "8A"

    def test_already_camelot_lowercase(self):
        assert _to_camelot("8a") == "8A"

    def test_musical_key_am(self):
        # Am（Aマイナー）→ Camelot 8A
        assert _to_camelot("Am") == "8A"

    def test_musical_key_dm(self):
        # Dm（Dマイナー）→ Camelot 7A
        assert _to_camelot("Dm") == "7A"

    def test_musical_key_c_major(self):
        # C（Cメジャー）→ Camelot 8B
        assert _to_camelot("C") == "8B"

    def test_musical_key_lowercase(self):
        # "am" → "Am" にして変換
        assert _to_camelot("am") == "8A"

    def test_boundary_wrap_12b(self):
        # B（Bメジャー）→ Camelot 1B
        assert _to_camelot("B") == "1B"

    def test_unknown_key_returns_none(self):
        assert _to_camelot("ZZ") is None

    def test_empty_string_returns_none(self):
        assert _to_camelot("") is None

    def test_fsharp_minor(self):
        # F#m → Camelot 11A
        assert _to_camelot("F#m") == "11A"


# ===========================================================================
# parse_rekordbox_csv の正常系テスト
# ===========================================================================

class TestParseNormal:
    def test_single_row_camelot_key(self):
        """Camelot 形式のキーを持つ 1 行を正常に処理できる。"""
        data = make_tsv("1\tInsomnia\tFaithless\t136.0\t8A")
        result = parse_rekordbox_csv(data)

        assert result["imported"] == 1
        assert result["skipped"] == 0
        track = result["tracks"][0]
        assert track["title"] == "Insomnia"
        assert track["artist"] == "Faithless"
        assert track["bpm"] == 136           # 小数点なし整数に変換されている
        assert track["key"] == "8A"
        assert track["energy"] == 5          # デフォルト値

    def test_single_row_musical_key(self):
        """Musical Key 形式（"Dm"）を Camelot（"7A"）に変換できる。"""
        data = make_tsv("1\tOne More Time\tDaft Punk\t123.0\tDm")
        result = parse_rekordbox_csv(data)

        assert result["imported"] == 1
        assert result["tracks"][0]["key"] == "7A"

    def test_multiple_rows(self):
        """複数行を正常にパースできる。"""
        data = make_tsv(
            "1\tTrack A\tArtist A\t128.0\t8A",
            "2\tTrack B\tArtist B\t140.0\tAm",
            "3\tTrack C\tArtist C\t 130\t11B",
        )
        result = parse_rekordbox_csv(data)
        assert result["imported"] == 3
        assert result["skipped"] == 0

    def test_bpm_float_to_int(self):
        """BPM が小数点付き文字列（"136.5"）でも整数（136）に変換される。"""
        data = make_tsv("1\tTitle\tArtist\t136.5\t8A")
        result = parse_rekordbox_csv(data)
        assert result["tracks"][0]["bpm"] == 136

    def test_custom_default_energy(self):
        """default_energy を指定した場合、その値が使われる。"""
        data = make_tsv("1\tTitle\tArtist\t128.0\t8A")
        result = parse_rekordbox_csv(data, default_energy=7)
        assert result["tracks"][0]["energy"] == 7

    def test_no_key_column_uses_default(self):
        """Musical Key 列がない場合、デフォルトキー "8A" が設定される。"""
        # ヘッダに Key 列なし
        tsv = "#\tTrack Title\tArtist\tBPM\n1\tTitle\tArtist\t128.0\n"
        result = parse_rekordbox_csv(tsv.encode("utf-8"))
        assert result["imported"] == 1
        assert result["tracks"][0]["key"] == "8A"

    def test_empty_lines_are_skipped_silently(self):
        """空行はスキップされ、skipped カウントに含まれない。"""
        data = make_tsv(
            "1\tTitle A\tArtist A\t128.0\t8A",
            "",
            "2\tTitle B\tArtist B\t130.0\t9B",
        )
        result = parse_rekordbox_csv(data)
        assert result["imported"] == 2
        assert result["skipped"] == 0

    def test_utf8_bom_encoding(self):
        """UTF-8 BOM 付きファイルを正しく読める。"""
        tsv = "#\tTrack Title\tArtist\tBPM\tMusical Key\n1\tTitle\tArtist\t128\t8A\n"
        bom_bytes = b"\xef\xbb\xbf" + tsv.encode("utf-8")
        result = parse_rekordbox_csv(bom_bytes)
        assert result["imported"] == 1

    def test_comma_separated_csv(self):
        """カンマ区切りCSVも自動判定して処理できる。"""
        csv_text = "#,Track Title,Artist,BPM,Musical Key\n1,Title,Artist,128.0,8A\n"
        result = parse_rekordbox_csv(csv_text.encode("utf-8"))
        assert result["imported"] == 1


# ===========================================================================
# parse_rekordbox_csv のスキップ・エラー系テスト
# ===========================================================================

class TestParseSkip:
    def test_bpm_out_of_range_low(self):
        """BPM が範囲外（40未満）の行はスキップされる。"""
        data = make_tsv("1\tTitle\tArtist\t30.0\t8A")
        result = parse_rekordbox_csv(data)
        assert result["imported"] == 0
        assert result["skipped"] == 1
        assert "BPM 30" in result["skip_reasons"][0]

    def test_bpm_out_of_range_high(self):
        """BPM が範囲外（250超）の行はスキップされる。"""
        data = make_tsv("1\tTitle\tArtist\t300.0\t8A")
        result = parse_rekordbox_csv(data)
        assert result["skipped"] == 1

    def test_bpm_not_numeric(self):
        """BPM が数値でない場合はスキップされる。"""
        data = make_tsv("1\tTitle\tArtist\tABCD\t8A")
        result = parse_rekordbox_csv(data)
        assert result["skipped"] == 1
        assert "数値でない" in result["skip_reasons"][0]

    def test_empty_title(self):
        """タイトルが空の行はスキップされる。"""
        data = make_tsv("1\t\tArtist\t128.0\t8A")
        result = parse_rekordbox_csv(data)
        assert result["skipped"] == 1
        assert "タイトルが空" in result["skip_reasons"][0]

    def test_empty_artist(self):
        """アーティスト名が空の行は 'Unknown' で補完されてインポートされる。"""
        data = make_tsv("1\tTitle\t\t128.0\t8A")
        result = parse_rekordbox_csv(data)
        assert result["imported"] == 1
        assert result["tracks"][0]["artist"] == "Unknown"

    def test_unknown_key_format(self):
        """認識できない Key 形式の行はスキップされる。"""
        data = make_tsv("1\tTitle\tArtist\t128.0\tXX")
        result = parse_rekordbox_csv(data)
        assert result["skipped"] == 1
        assert "認識できない形式" in result["skip_reasons"][0]

    def test_mixed_valid_and_invalid(self):
        """有効な行と無効な行が混在する場合、有効な行だけが登録される。"""
        data = make_tsv(
            "1\tValid Track\tArtist\t128.0\t8A",   # ← OK
            "2\tBad BPM Track\tArtist\t999.0\t8A", # ← BPM 範囲外
            "3\tAnother Track\tArtist\t130.0\tDm", # ← OK
        )
        result = parse_rekordbox_csv(data)
        assert result["imported"] == 2
        assert result["skipped"] == 1

    def test_file_too_large(self):
        """ファイルサイズが上限（5MB）を超えた場合はエラーメッセージを返す。"""
        big_data = b"x" * (MAX_FILE_SIZE + 1)
        result = parse_rekordbox_csv(big_data)
        assert result["imported"] == 0
        assert "5MB" in result["skip_reasons"][0]

    def test_empty_file(self):
        """空ファイルでは 0 件の結果を返す。"""
        result = parse_rekordbox_csv(b"")
        assert result["imported"] == 0

    def test_no_header_row(self):
        """ヘッダ行がないファイルはエラーメッセージを返す。"""
        data = b"random text\nno header here\n"
        result = parse_rekordbox_csv(data)
        assert result["imported"] == 0
        assert result["skip_reasons"]

    def test_missing_required_columns(self):
        """必須列（Track Title, Artist, BPM）が欠けている場合はエラーを返す。"""
        tsv = "#\tTrack Title\tBPM\n1\tTitle\t128\n"  # Artist 列がない
        result = parse_rekordbox_csv(tsv.encode("utf-8"))
        assert result["imported"] == 0
        assert "Artist" in result["skip_reasons"][0]
