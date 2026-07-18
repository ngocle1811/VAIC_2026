"""SQLAlchemy session and declarative model foundation."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Authoritative SQLAlchemy declarative base."""


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    return sessionmaker(bind=engine, expire_on_commit=False)


@lru_cache(maxsize=4)
def get_session_factory(database_url: str) -> sessionmaker[Session]:
    """Reuse one engine and pool for each configured database URL."""
    return create_session_factory(database_url)


def get_session() -> Iterator[Session]:
    factory = get_session_factory(get_settings().database_url)
    with factory() as session:
        yield session
