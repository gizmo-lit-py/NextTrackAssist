"""
003: tracks.key に Camelot Wheel の CHECK 制約を追加する。

これまで Camelot 妥当性はアプリ側 (services/score.py, services/rekordbox.py) で
担保されていたが、DB レイヤーでも不正値を弾くようにしてデータ完全性を高める。
許容値は 1A〜12A / 1B〜12B の 24 値のみ。

各方言での扱い:
  - PostgreSQL / MySQL: ALTER TABLE ... ADD CONSTRAINT で追加
  - SQLite:             CHECK の追加に ALTER TABLE が使えないので、
                        テーブル再構築 (002 と同じ手筋) で適用する
"""

from sqlalchemy import inspect, text


CAMELOT_KEYS = [
    "1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B",
    "5A", "5B", "6A", "6B", "7A", "7B", "8A", "8B",
    "9A", "9B", "10A", "10B", "11A", "11B", "12A", "12B",
]
CAMELOT_IN_LIST = ", ".join(f"'{k}'" for k in CAMELOT_KEYS)
CHECK_NAME = "check_key_camelot"


def _is_sqlite(engine) -> bool:
    return engine.dialect.name == "sqlite"


def _has_constraint_pg(engine) -> bool:
    with engine.begin() as conn:
        result = conn.execute(text(
            "SELECT 1 FROM pg_constraint "
            "WHERE conname = :name AND conrelid = 'tracks'::regclass"
        ), {"name": CHECK_NAME}).first()
        return result is not None


def _has_constraint_mysql(engine) -> bool:
    with engine.begin() as conn:
        result = conn.execute(text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = 'tracks' AND constraint_name = :name"
        ), {"name": CHECK_NAME}).first()
        return result is not None


def _has_constraint_sqlite(engine) -> bool:
    """SQLite では sqlite_master の sql 文字列に CHECK 名が出てくるかで判定する。"""
    with engine.begin() as conn:
        row = conn.execute(text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='tracks'"
        )).first()
        if row is None:
            # tracks テーブル自体がまだ無い場合は create_all 側で最新スキーマが
            # 作られているはずなので、何もしなくてOK
            return True
        sql = (row[0] or "").lower()
        return CHECK_NAME in sql


def upgrade(engine):
    insp = inspect(engine)
    if "tracks" not in insp.get_table_names():
        print("[migrate 003] tracks テーブルが存在しません。スキップします。")
        return

    if _is_sqlite(engine):
        if _has_constraint_sqlite(engine):
            print("[migrate 003] check_key_camelot は既に存在します (sqlite)。スキップします。")
            return
        # SQLite はテーブル再構築で CHECK を追加する
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys = OFF"))
            conn.execute(text(f"""
                CREATE TABLE tracks_new (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    artist VARCHAR(255) NOT NULL,
                    bpm FLOAT NOT NULL,
                    key VARCHAR(3) NOT NULL,
                    energy INTEGER NOT NULL,
                    CONSTRAINT check_bpm_range CHECK (bpm BETWEEN 40 AND 250),
                    CONSTRAINT check_energy_range CHECK (energy BETWEEN 1 AND 10),
                    CONSTRAINT {CHECK_NAME} CHECK (key IN ({CAMELOT_IN_LIST})),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("""
                INSERT INTO tracks_new (id, user_id, title, artist, bpm, key, energy)
                SELECT id, user_id, title, artist, bpm, key, energy FROM tracks
            """))
            conn.execute(text("DROP TABLE tracks"))
            conn.execute(text("ALTER TABLE tracks_new RENAME TO tracks"))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_tracks_user_id ON tracks(user_id)"
            ))
            conn.execute(text("PRAGMA foreign_keys = ON"))
        print("[migrate 003] tracks に check_key_camelot を追加しました (sqlite, rebuild).")
        return

    if engine.dialect.name == "postgresql":
        if _has_constraint_pg(engine):
            print("[migrate 003] check_key_camelot は既に存在します (postgres)。スキップします。")
            return
        with engine.begin() as conn:
            conn.execute(text(
                f"ALTER TABLE tracks ADD CONSTRAINT {CHECK_NAME} "
                f"CHECK (key IN ({CAMELOT_IN_LIST}))"
            ))
        print("[migrate 003] tracks に check_key_camelot を追加しました (postgres).")
        return

    # mysql / mariadb
    if _has_constraint_mysql(engine):
        print("[migrate 003] check_key_camelot は既に存在します (mysql)。スキップします。")
        return
    with engine.begin() as conn:
        conn.execute(text(
            f"ALTER TABLE tracks ADD CONSTRAINT {CHECK_NAME} "
            f"CHECK (key IN ({CAMELOT_IN_LIST}))"
        ))
    print("[migrate 003] tracks に check_key_camelot を追加しました (mysql).")
