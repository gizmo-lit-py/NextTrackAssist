import sqlite3
from pathlib import Path

# データベースファイルの場所
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"

def get_connection():
    """DB接続を返す"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """テーブル作成"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    bpm REAL NOT NULL,
    key TEXT NOT NULL,
    energy INTEGER NOT NULL CHECK (energy BETWEEN 1 AND 10),
    genre TEXT NOT NULL CHECK (
        genre IN (
            'trap',
            'drill',
            'rage',
            'rnb',
            'boom_bap',
            'lofi'
        )
    ),
    mix_window_sec INTEGER DEFAULT 120,
    created_at TEXT NOT NULL
);
""")
    
    conn.commit()
    conn.close()

