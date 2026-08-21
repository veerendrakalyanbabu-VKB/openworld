"""Database session management."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from core.db.base import Base

_engine = None
_SessionLocal = None


def init_engine(database_url: str, *, echo: bool = False):
    global _engine, _SessionLocal
    connect_args: dict = {}
    pool_kwargs: dict = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if ":memory:" in database_url:
            pool_kwargs["poolclass"] = StaticPool
    _engine = create_engine(database_url, echo=echo, connect_args=connect_args, **pool_kwargs)
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_engine():
    if _engine is None:
        raise RuntimeError("Database engine not initialized")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        raise RuntimeError("Database session factory not initialized")
    return _SessionLocal


def create_all_tables():
    Base.metadata.create_all(bind=get_engine())


def drop_all_tables():
    Base.metadata.drop_all(bind=get_engine())


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for DB sessions."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
