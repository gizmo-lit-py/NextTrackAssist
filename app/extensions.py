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
    engine_kwargs.update(
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

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