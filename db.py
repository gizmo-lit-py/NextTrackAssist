import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ==============================
# 環境変数読み込み
# ==============================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

# ==============================
# Engine設定（本番想定）
# ==============================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True  # 接続切れ自動検知
)

# ==============================
# Session設定（実務標準）
# ==============================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ==============================
# Base
# ==============================

Base = declarative_base()