import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from simplebank.database import get_db
from simplebank.models.models import Base
from simplebank.models import models
from simplebank.utils.security_deps import API_KEY, SECURITY_HEADERS, SecurityAudit
from simplebank.main import app
from simplebank.init_db import init_customers
from unittest.mock import patch, MagicMock
import time
from datetime import datetime, timedelta
import base64
import json

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

@pytest.fixture
def client(test_db):
    return TestClient(app)

@pytest.fixture
def sample_transactions():
    """Create sample transactions using the existing accounts"""
    db = TestingSessionLocal()
    try:
        # Get the first two customers
        customers = db.query(models.Customer).limit(2).all()
        
        # Create two test accounts
        account1 = models.Account(
            customer_id=customers[0].id,
            balance=1000.0
        )
        account2 = models.Account(
            customer_id=customers[1].id,
            balance=1000.0
        )
        db.add_all([account1, account2])
        db.commit()
        db.refresh(account1)
        db.refresh(account2)
        
        print(f"Created test accounts: {account1.id} and {account2.id}")

        # Create transactions with different timestamps
        base_time = datetime(2024, 1, 1, 12, 0)
        transactions = []
        
        for i in range(25):  # Create 25 transactions
            tx = models.Transaction(
                from_account_id=account1.id,
                to_account_id=account2.id,
                amount=100 + i,
                timestamp=base_time - timedelta(hours=i)  # Transactions spread over time
            )
            transactions.append(tx)
        
        db.add_all(transactions)
        db.commit()
        
        # Print debug information about created transactions
        created_transactions = db.query(models.Transaction).filter(
            models.Transaction.from_account_id == account1.id
        ).order_by(models.Transaction.timestamp.desc()).all()
        
        print(f"\nCreated {len(created_transactions)} transactions")
        print("Sample of transaction timestamps:")
        for tx in created_transactions[:3]:
            print(f"ID: {tx.id}, Timestamp: {tx.timestamp}, From: {tx.from_account_id}, To: {tx.to_account_id}")
        
        return created_transactions
    finally:
        db.close()

class TestGeneralFeatures:
    def test_read_customers(self,client):
        response = client.get("/api/customers",headers={"X-API-Key": API_KEY})
        assert response.status_code == 200
        customers = response.json()
        assert len(customers) == 4
        assert customers[0]["name"] == "Arisha Barron"

    def test_create_customer(self,client):
        response = client.post("/api/customers", json={"name": "John Doe"},headers={"X-API-Key": API_KEY})
        assert response.status_code == 200
        customer = response.json()
        assert customer["name"] == "John Doe"

    def test_get_customer(self,client):
        response = client.get("/api/customers/1",headers={"X-API-Key": API_KEY})
        assert response.status_code == 200
        customer = response.json()
        assert customer["name"] == "Arisha Barron"

    def test_create_account(self,client):
        response = client.post(
            "/api/accounts",
            json={"customer_id": 1, "initial_deposit": 100.0}, headers={"X-API-Key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == 1
        assert data["balance"] == 100.0

    def test_get_account_balance(self,client):
        # First create an account
        account_response = client.post(
            "/api/accounts",
            json={"customer_id": 1, "initial_deposit": 500.0}, headers={"X-API-Key": API_KEY}
        )
        account_id = account_response.json()["id"]
        
        # Then get its balance
        balance_response = client.get(f"/api/accounts/{account_id}/balance",headers={"X-API-Key": API_KEY})
        assert balance_response.status_code == 200
        data = balance_response.json()
        assert data["account_id"] == account_id
        assert data["balance"] == 500.0


    def test_transfer_money(self,client):
        # Create two accounts
        account1_response = client.post(
            "/api/accounts",
            json={"customer_id": 1, "initial_deposit": 1000.0}, headers={"X-API-Key": API_KEY}
        )
        account1_id = account1_response.json()["id"]
        
        account2_response = client.post(
            "/api/accounts",
            json={"customer_id": 2, "initial_deposit": 500.0}, headers={"X-API-Key": API_KEY}
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
            }, headers={"X-API-Key": API_KEY}
        )
        assert transfer_response.status_code == 200
        
        # Check balances after transfer
        balance1_response = client.get(f"/api/accounts/{account1_id}/balance",headers={"X-API-Key": API_KEY})
        balance1 = balance1_response.json()["balance"]
        assert balance1 == 1000.0 - transfer_amount
        
        balance2_response = client.get(f"/api/accounts/{account2_id}/balance",headers={"X-API-Key": API_KEY})
        balance2 = balance2_response.json()["balance"]
        assert balance2 == 500.0 + transfer_amount

    def test_insufficient_funds(self,client):
        # Create an account with a small balance
        account_response = client.post(
            "/api/accounts",
            json={"customer_id": 1, "initial_deposit": 50.0}, headers={"X-API-Key": API_KEY}
        )
        account1_id = account_response.json()["id"]
        
        # Create a second account
        account2_response = client.post(
            "/api/accounts",
            json={"customer_id": 2, "initial_deposit": 100.0}, headers={"X-API-Key": API_KEY}
        )
        account2_id = account2_response.json()["id"]
        
        # Try to transfer more money than available
        transfer_response = client.post(
            "/api/transactions",
            json={
                "from_account_id": account1_id,
                "to_account_id": account2_id,
                "amount": 100.0  # More than the 50.0 available
            }, headers={"X-API-Key": API_KEY}
        )
        assert transfer_response.status_code == 400  # Bad request - insufficient funds

    def test_transfer_history(self,client):
        # Create two accounts
        account1_response = client.post(
            "/api/accounts",
            json={"customer_id": 1, "initial_deposit": 1000.0}, headers={"X-API-Key": API_KEY}
        )
        account1_id = account1_response.json()["id"]
        
        account2_response = client.post(
            "/api/accounts",
            json={"customer_id": 2, "initial_deposit": 500.0}, headers={"X-API-Key": API_KEY}
        )
        account2_id = account2_response.json()["id"]
        
        # Make a couple of transfers
        client.post(
            "/api/transactions",
            json={
                "from_account_id": account1_id,
                "to_account_id": account2_id,
                "amount": 200.0
            }, headers={"X-API-Key": API_KEY}
        )
        
        client.post(
            "/api/transactions",
            json={
                "from_account_id": account2_id,
                "to_account_id": account1_id,
                "amount": 50.0
            }, headers={"X-API-Key": API_KEY}
        )
        
        # Get transfer history for account1
        history_response = client.get(f"/api/accounts/{account1_id}/transactions",headers={"X-API-Key": API_KEY})
        assert history_response.status_code == 200
        data = history_response.json()
        
        # Check for the paginated format
        assert "items" in data
        assert len(data["items"]) == 2  # Should have 2 transactions
        
        # Verify that all transactions are related to this account
        for tx in data["items"]:
            assert tx["from_account_id"] == account1_id or tx["to_account_id"] == account1_id


class TestSecurityFeatures:
    
    def test_missing_api_key(self,client):
        """Test that requests without API key are rejected"""
        response = client.get("/api/customers/1")
        assert response.status_code == 401
        assert "Invalid or missing API key" in response.json()["detail"]
    
    def test_invalid_api_key(self,client):
        """Test that requests with invalid API key are rejected"""
        response = client.get("/api/customers/1", headers={"X-API-Key": "invalid_key"})
        assert response.status_code == 401
        assert "Invalid or missing API key" in response.json()["detail"]
    
    def test_valid_api_key(self,client):
        """Test that requests with valid API key are accepted"""
        response = client.get("/api/customers/1", headers={"X-API-Key": API_KEY})
        # Even if the customer doesn't exist, we should get past the API key check
        assert response.status_code != 401
    
    def test_security_headers(self,client):
        """Test that security headers are added to responses"""
        response = client.get("/api/customers/1", headers={"X-API-Key": API_KEY})
        
        # Check that security headers were added
        for header, value in SECURITY_HEADERS.items():
            assert response.headers.get(header) == value
    
    @patch('simplebank.utils.security_deps.check_rate_limit')
    def test_rate_limiting(self, mock_check_rate_limit, client):
        """Test that rate limiting is enforced"""
        # First set the mock to return False (rate limit exceeded)
        mock_check_rate_limit.return_value = False
        
        response = client.get("/api/customers/1", headers={"X-API-Key": API_KEY})
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
        
        # Then set it to return True
        mock_check_rate_limit.return_value = True
        
        response = client.get("/api/customers/1", headers={"X-API-Key": API_KEY})
        assert response.status_code != 429
    
    
    @pytest.mark.asyncio
    async def test_security_audit_class(self):
        """Test the SecurityAudit class directly"""
        # Create mock request and response
        mock_request = MagicMock()
        mock_request.state.start_time = time.time() - 1  # 1 second ago
        mock_request.method = "GET"
        mock_request.url.path = "/api/customers/1"
        mock_request.client.host = "127.0.0.1"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        
        # Create SecurityAudit instance
        audit = SecurityAudit(operation_name="Test Operation")
        
        # Test the audit
        with patch('simplebank.utils.security_deps.log_request') as mock_log:
            result = await audit(mock_request, mock_response)
            assert result == True
            mock_log.assert_called_once()
            
            # Check security headers were added
            for header, value in SECURITY_HEADERS.items():
                assert mock_response.headers.get(header) == value

class TestPaginationFeatures:
    def test_transaction_pagination_basic(self, client, sample_transactions):
        """Test basic pagination of transactions endpoint"""
        # Get the first account ID from the sample transactions
        first_account_id = sample_transactions[0].from_account_id
        print(f"\nTesting pagination for account ID: {first_account_id}")
        
        # Get first page
        headers = {"X-API-Key": API_KEY}
        response = client.get(f"/api/accounts/{first_account_id}/transactions?limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "next_cursor" in data
        assert len(data["items"]) == 10
        
        # Get second page using cursor
        next_cursor = data["next_cursor"]
        response2 = client.get(
            f"/api/accounts/{first_account_id}/transactions?limit=10&cursor={next_cursor}",
            headers=headers
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Decode and print cursor contents for debugging
        try:
            decoded = base64.b64decode(next_cursor).decode('utf-8')
            cursor_data = json.loads(decoded)
            print(f"Decoded cursor: {cursor_data}")
        except Exception as e:
            print(f"Error decoding cursor: {e}")
        
        assert len(data2["items"]) == 10
        
        # Verify no duplicate transactions between pages
        first_page_ids = {item["id"] for item in data["items"]}
        second_page_ids = {item["id"] for item in data2["items"]}
        assert not (first_page_ids & second_page_ids), "Found duplicate IDs between pages"


    def test_transaction_pagination_last_page(self, client, sample_transactions):
        """Test pagination behavior on the last page"""
        first_account_id = sample_transactions[0].from_account_id
        
        headers = {"X-API-Key": API_KEY}
        response = client.get(f"/api/accounts/{first_account_id}/transactions?limit=20", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        next_cursor = data["next_cursor"]
        assert next_cursor is not None
        
        # Get final page
        response2 = client.get(
            f"/api/accounts/{first_account_id}/transactions?limit=20&cursor={next_cursor}",
            headers=headers
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Should be less than full page and no next cursor
        assert len(data2["items"]) < 20
        assert data2["next_cursor"] is None
        
        # Verify we have exactly the expected number of items across all pages
        total_items = len(data["items"]) + len(data2["items"])
        assert total_items == 25, f"Expected 25 total items, got {total_items}"

