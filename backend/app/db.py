import os
from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from backend.app.settings import settings


def _effective_database_url() -> str:
    return os.environ.get("DATABASE_URL", settings.database_url)


def engine():
    url = _effective_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, echo=False, connect_args=connect_args)


_ENGINE = engine()


def init_db() -> None:
    os.makedirs("backend/data", exist_ok=True)
    SQLModel.metadata.create_all(_ENGINE)


@contextmanager
def session() -> Iterator[Session]:
    with Session(_ENGINE) as s:
        yield s

