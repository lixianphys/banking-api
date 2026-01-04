import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock
import fakeredis
from typing import Generator
from passlib.context import CryptContext

from simplebank.database import get_db, get_db_async
from simplebank.models.models import Base, User, Customer, Account, Transaction  # Import all models to ensure tables are created
from simplebank.main import app
from simplebank.utils.jwt_utils import create_access_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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


@pytest.fixture
def test_user(test_db):
    """Create a test user and return user object and JWT token"""
    db = TestingSessionLocal()
    try:
        # Create test user directly in database
        hashed_password = pwd_context.hash("testpassword123")
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hashed_password,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create JWT token
        token_data = {"sub": user.username, "user_id": user.id}
        access_token = create_access_token(token_data)
        
        yield user, access_token
    finally:
        db.close()


@pytest.fixture
def auth_headers(test_user):
    """Return authorization headers with JWT token"""
    user, token = test_user
    return {"Authorization": f"Bearer {token}"}

