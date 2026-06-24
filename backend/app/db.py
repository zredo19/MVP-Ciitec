"""
Capa de acceso a datos. SQLAlchemy síncrono (psycopg3).

Se usa modo síncrono a propósito: el worker Celery (prefork) y el pipeline
comparten exactamente el mismo ORM/sesión sin la fricción de async en procesos
fork. FastAPI ejecuta los endpoints síncronos en su threadpool.

El esquema lo crea `db/schema.sql` en el init del contenedor; aquí NO se hace
create_all: los modelos solo mapean tablas existentes.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI: una sesión por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
