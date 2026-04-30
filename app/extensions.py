from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from app.config import Config

url = make_url(Config.SQLALCHEMY_DATABASE_URI)
engine_kwargs = {
    "future": True,
}

if url.get_backend_name() == "sqlite":
    # SQLite はファイル/メモリ DB なので「接続切れ」を心配する必要がない。
    # 一方でマルチスレッド環境（Flask + テスト）では同一接続を使い回したいので
    # StaticPool + check_same_thread=False を指定する。
    engine_kwargs.update(
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL/MySQL 等のリモート DB では、ネットワーク切断やアイドルタイムアウト
    # で接続が死んでいることがある。pool_pre_ping=True にしておくと、接続を
    # プールから取り出す前に軽量な ping を打って死活確認してくれる。
    # README の運用設計セクションでも約束している挙動。
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    **engine_kwargs,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
    expire_on_commit=False,
)

Base = declarative_base()