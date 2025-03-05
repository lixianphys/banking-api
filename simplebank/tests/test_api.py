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


def test_transfer_money(test_db):
    # Create two accounts
    account1_response = client.post(
        "/api/accounts",
        json={"customer_id": 1, "initial_deposit": 1000.0}
    )
    account1_id = account1_response.json()["id"]
    
    account2_response = client.post(
        "/api/accounts",
        json={"customer_id": 2, "initial_deposit": 500.0}
    )
    account2_id = account2_response.json()["id"]
    
    # Transfer money from account1 to account2
    transfer_amount = 300.0
    transfer_response = client.post(
        "/api/transactions",
        json={
            "from_account_id": account1_id,
            "to_account_id": account2_id,
            "amount": transfer_amount
        }
    )
    assert transfer_response.status_code == 200
    
    # Check balances after transfer
    balance1_response = client.get(f"/api/accounts/{account1_id}/balance")
    balance1 = balance1_response.json()["balance"]
    assert balance1 == 1000.0 - transfer_amount
    
    balance2_response = client.get(f"/api/accounts/{account2_id}/balance")
    balance2 = balance2_response.json()["balance"]
    assert balance2 == 500.0 + transfer_amount

def test_insufficient_funds(test_db):
    # Create an account with a small balance
    account_response = client.post(
        "/api/accounts",
        json={"customer_id": 1, "initial_deposit": 50.0}
    )
    account1_id = account_response.json()["id"]
    
    # Create a second account
    account2_response = client.post(
        "/api/accounts",
        json={"customer_id": 2, "initial_deposit": 100.0}
    )
    account2_id = account2_response.json()["id"]
    
    # Try to transfer more money than available
    transfer_response = client.post(
        "/api/transactions",
        json={
            "from_account_id": account1_id,
            "to_account_id": account2_id,
            "amount": 100.0  # More than the 50.0 available
        }
    )
    assert transfer_response.status_code == 400  # Bad request - insufficient funds

def test_transfer_history(test_db):
    # Create two accounts
    account1_response = client.post(
        "/api/accounts",
        json={"customer_id": 1, "initial_deposit": 1000.0}
    )
    account1_id = account1_response.json()["id"]
    
    account2_response = client.post(
        "/api/accounts",
        json={"customer_id": 2, "initial_deposit": 500.0}
    )
    account2_id = account2_response.json()["id"]
    
    # Make a couple of transfers
    client.post(
        "/api/transactions",
        json={
            "from_account_id": account1_id,
            "to_account_id": account2_id,
            "amount": 200.0
        }
    )
    
    client.post(
        "/api/transactions",
        json={
            "from_account_id": account2_id,
            "to_account_id": account1_id,
            "amount": 50.0
        }
    )
    
    # Get transfer history for account1
    history_response = client.get(f"/api/accounts/{account1_id}/transactions")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["account_id"] == account1_id
    assert len(history["transactions"]) == 2 