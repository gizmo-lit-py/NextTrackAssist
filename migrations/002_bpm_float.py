"""
002: tracks.bpm を Integer から Float (REAL) に変更する。

既存の整数BPM（例: 128）はそのまま 128.0 として保持される。
SQLite は ALTER COLUMN を直接サポートしないため、
- PostgreSQL/MySQL: ALTER TABLE ... ALTER COLUMN
- SQLite:           テーブルを作り直して移行
の両方に対応する。
"""

from sqlalchemy import inspect, text


def _is_sqlite(engine) -> bool:
    return engine.dialect.name == "sqlite"


def _column_already_float(engine) -> bool:
    """tracks.bpm がすでに浮動小数点型かどうかを確認する。"""
    insp = inspect(engine)
    if "tracks" not in insp.get_table_names():
        return False
    for col in insp.get_columns("tracks"):
        if col["name"] == "bpm":
            type_str = str(col["type"]).upper()
            return any(t in type_str for t in ("FLOAT", "REAL", "DOUBLE", "NUMERIC"))
    return False


def upgrade(engine):
    if _column_already_float(engine):
        print("[migrate 002] tracks.bpm はすでに Float 型です。スキップします。")
        return

    if _is_sqlite(engine):
        # SQLite はカラム型変更ができないので、テーブルを作り直す。
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys = OFF"))
            conn.execute(text("""
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
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("""
                INSERT INTO tracks_new (id, user_id, title, artist, bpm, key, energy)
                SELECT id, user_id, title, artist, CAST(bpm AS REAL), key, energy
                FROM tracks
            """))
            conn.execute(text("DROP TABLE tracks"))
            conn.execute(text("ALTER TABLE tracks_new RENAME TO tracks"))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_tracks_user_id ON tracks(user_id)"
            ))
            conn.execute(text("PRAGMA foreign_keys = ON"))
    else:
        # PostgreSQL / MySQL は ALTER COLUMN で型変更可能
        with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(text(
                    "ALTER TABLE tracks "
                    "ALTER COLUMN bpm TYPE DOUBLE PRECISION USING bpm::double precision"
                ))
            else:  # mysql / mariadb
                conn.execute(text("ALTER TABLE tracks MODIFY COLUMN bpm DOUBLE NOT NULL"))

    print("[migrate 002] tracks.bpm を Float に変更しました。")
