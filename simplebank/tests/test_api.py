import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from simplebank.database import get_db
from simplebank.models.models import Base
from simplebank.main import app
from simplebank.api.customers import init_customers

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool)

TestingSessionLocal = sessionmaker(bind=engine)

# Override the get_db dependency for testing
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create a test client
client = TestClient(app)

@pytest.fixture(scope="function")
def test_db():
    # Create the tables
    Base.metadata.create_all(bind=engine)
    # Initialize test database with sample data
    db = TestingSessionLocal()
    init_customers(db)
    db.close()

    yield
    
    # Drop all tables after test
    Base.metadata.drop_all(bind=engine)

def test_read_customers(test_db):
    response = client.get("/api/customers")
    assert response.status_code == 200
    customers = response.json()
    assert len(customers) == 4
    assert customers[0]["name"] == "Arisha Barron"

def test_create_customer(test_db):
    response = client.post("/api/customers", json={"name": "John Doe"})
    assert response.status_code == 200
    customer = response.json()
    assert customer["name"] == "John Doe"

def test_get_customer(test_db):
    response = client.get("/api/customers/1")
    assert response.status_code == 200
    customer = response.json()
    assert customer["name"] == "Arisha Barron"

def test_create_account(test_db):
    response = client.post(
        "/api/accounts",
        json={"customer_id": 1, "initial_deposit": 100.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == 1
    assert data["balance"] == 100.0

def test_get_account_balance(test_db):
    # First create an account
    account_response = client.post(
        "/api/accounts",
        json={"customer_id": 1, "initial_deposit": 500.0}
    )
    account_id = account_response.json()["id"]
    
    # Then get its balance
    balance_response = client.get(f"/api/accounts/{account_id}/balance")
    assert balance_response.status_code == 200
    data = balance_response.json()
    assert data["account_id"] == account_id
    assert data["balance"] == 500.0