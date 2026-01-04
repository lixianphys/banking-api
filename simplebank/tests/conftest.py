import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock
import fakeredis
from typing import Generator

from simplebank.database import get_db, get_db_async
from simplebank.models.models import Base, User, Customer, Account, Transaction  # Import all models to ensure tables are created
from simplebank.main import app

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(bind=engine)


# Override the get_db dependency for testing
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Override async database dependency to use sync database for testing
async def override_get_db_async():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db_async] = override_get_db_async


@pytest.fixture(scope="function")
def test_db():
    """Create and drop tables for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis client using fakeredis for testing"""
    return fakeredis.FakeStrictRedis(decode_responses=True)


@pytest.fixture
def db_session():
    """Database session fixture"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        db.rollback()

