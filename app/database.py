import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./food_stock.db",
)

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(
    dbapi_connection,
    _connection_record,
):
    """SQLite接続時に外部キー制約を有効にする。"""
    if not DATABASE_URL.startswith("sqlite"):
        return

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

    
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()