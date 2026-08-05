from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# モデルをBase.metadataへ登録するためにimportする。
from app.models.ingredient import Ingredient  # noqa: F401
from app.models.inventory import Inventory  # noqa: F401



TEST_DATABASE_URL = "sqlite://"


test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """各テストで独立したテスト用DBを提供する。"""
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    try:
        yield db

    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(
    db_session: Session,
) -> Generator[TestClient, None, None]:
    """テスト用DBへ接続するTestClientを提供する。"""

    def override_get_db():
        try:
            yield db_session

        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()