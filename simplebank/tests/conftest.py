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

# Use in-memory SQLite for testing with shared connection
# Using file-based in-memory SQLite to ensure all connections see the same database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create engine with StaticPool to ensure single connection
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    pool_pre_ping=True
)

TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


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
def test_user(test_db, client):
    """Create a test user via API and return user object and JWT token"""
    # Register user via API to ensure it's in the same database session
    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    register_response = client.post("/api/auth/register", json=register_data)
    assert register_response.status_code == 201
    user_data = register_response.json()
    
    # Login to get token
    login_data = {
        "username": "testuser",
        "password": "testpassword123"
    }
    login_response = client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200
    tokens = login_response.json()
    access_token = tokens["access_token"]
    
    # Create a mock user object from the response data
    # We can't query the database due to SQLite in-memory connection issues
    # So we create a minimal user object with the data we need
    user = User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        is_active=user_data["is_active"]
    )
    
    yield user, access_token


@pytest.fixture
def auth_headers(test_user):
    """Return authorization headers with JWT token"""
    user, token = test_user
    return {"Authorization": f"Bearer {token}"}

