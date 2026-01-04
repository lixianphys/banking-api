import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from passlib.context import CryptContext

from simplebank.main import app
from simplebank.models.models import User
from simplebank.tests.conftest import TestingSessionLocal, test_db
from simplebank.utils.jwt_utils import create_access_token, create_refresh_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_register_success(self, client, test_db):
        """Test successful user registration"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123"
        }
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "hashed_password" not in data  # Password should not be returned
        assert data["is_active"] is True

    def test_register_duplicate_username(self, client, test_db):
        """Test registration with duplicate username"""
        user_data = {
            "username": "testuser",
            "email": "test1@example.com",
            "password": "password123"
        }
        # Create first user
        client.post("/api/auth/register", json=user_data)
        
        # Try to register again with same username
        user_data2 = {
            "username": "testuser",
            "email": "test2@example.com",
            "password": "password123"
        }
        response = client.post("/api/auth/register", json=user_data2)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_email(self, client, test_db):
        """Test registration with duplicate email"""
        user_data = {
            "username": "user1",
            "email": "test@example.com",
            "password": "password123"
        }
        # Create first user
        client.post("/api/auth/register", json=user_data)
        
        # Try to register again with same email
        user_data2 = {
            "username": "user2",
            "email": "test@example.com",
            "password": "password123"
        }
        response = client.post("/api/auth/register", json=user_data2)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_short_password(self, client, test_db):
        """Test registration with password too short"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "short"  # Less than 8 characters
        }
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error

    def test_login_success(self, client, test_db):
        """Test successful login"""
        # Register a user first
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        client.post("/api/auth/register", json=user_data)
        
        # Login
        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        with patch('simplebank.api.auth.store_refresh_token', return_value=True):
            response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    def test_login_invalid_username(self, client, test_db):
        """Test login with invalid username"""
        login_data = {
            "username": "nonexistent",
            "password": "password123"
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_invalid_password(self, client, test_db):
        """Test login with invalid password"""
        # Register a user first
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        client.post("/api/auth/register", json=user_data)
        
        # Try to login with wrong password
        login_data = {
            "username": "testuser",
            "password": "wrongpassword"
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_inactive_user(self, client, test_db):
        """Test login with inactive user"""
        db = TestingSessionLocal()
        try:
            # Create inactive user
            hashed = pwd_context.hash("password123")
            user = User(
                username="inactiveuser",
                email="inactive@example.com",
                hashed_password=hashed,
                is_active=False
            )
            db.add(user)
            db.commit()
        finally:
            db.close()
        
        login_data = {
            "username": "inactiveuser",
            "password": "password123"
        }
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    def test_refresh_token_success(self, client, test_db):
        """Test successful token refresh"""
        db = TestingSessionLocal()
        try:
            # Create user
            hashed = pwd_context.hash("password123")
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password=hashed
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create refresh token
            refresh_token_data = {"sub": user.username, "user_id": user.id}
            refresh_token = create_refresh_token(refresh_token_data)
            
            # Store refresh token in Redis (mocked)
            with patch('simplebank.api.auth.get_refresh_token', return_value={"user_id": user.id, "token": refresh_token}):
                with patch('simplebank.api.auth.is_token_blacklisted', return_value=False):
                    response = client.post(
                        "/api/auth/refresh",
                        headers={"Refresh-Token": refresh_token}
                    )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
        finally:
            db.close()

    def test_refresh_token_invalid(self, client, test_db):
        """Test refresh with invalid token"""
        invalid_token = "invalid.token.here"
        with patch('simplebank.api.auth.verify_token', return_value=None):
            response = client.post(
                "/api/auth/refresh",
                headers={"Refresh-Token": invalid_token}
            )
        assert response.status_code == 401

    def test_refresh_token_blacklisted(self, client, test_db):
        """Test refresh with blacklisted token"""
        db = TestingSessionLocal()
        try:
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            refresh_token_data = {"sub": user.username, "user_id": user.id}
            refresh_token = create_refresh_token(refresh_token_data)
            
            with patch('simplebank.api.auth.verify_token', return_value=MagicMock(username="testuser", user_id=user.id)):
                with patch('simplebank.api.auth.is_token_blacklisted', return_value=True):
                    response = client.post(
                        "/api/auth/refresh",
                        headers={"Refresh-Token": refresh_token}
                    )
            assert response.status_code == 401
        finally:
            db.close()

    def test_logout_success(self, client, test_db):
        """Test successful logout"""
        db = TestingSessionLocal()
        try:
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create access token
            access_token_data = {"sub": user.username, "user_id": user.id}
            access_token = create_access_token(access_token_data)
            
            with patch('simplebank.api.auth.verify_token', return_value=MagicMock(username="testuser", user_id=user.id)):
                with patch('simplebank.api.auth.add_to_blacklist', return_value=True):
                    response = client.post(
                        "/api/auth/logout",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
            
            assert response.status_code == 200
            assert "logged out" in response.json()["message"].lower()
        finally:
            db.close()

    def test_logout_invalid_token(self, client, test_db):
        """Test logout with invalid token"""
        invalid_token = "invalid.token"
        with patch('simplebank.api.auth.verify_token', return_value=None):
            response = client.post(
                "/api/auth/logout",
                headers={"Authorization": f"Bearer {invalid_token}"}
            )
        assert response.status_code == 401

    def test_get_current_user_success(self, client, test_db):
        """Test getting current user info"""
        db = TestingSessionLocal()
        try:
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create access token
            access_token_data = {"sub": user.username, "user_id": user.id}
            access_token = create_access_token(access_token_data)
            
            with patch('simplebank.api.auth.get_current_user') as mock_get_user:
                mock_get_user.return_value = user
                response = client.get(
                    "/api/auth/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
        finally:
            db.close()

    def test_get_current_user_no_token(self, client, test_db):
        """Test getting current user without token"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client, test_db):
        """Test getting current user with invalid token"""
        invalid_token = "invalid.token"
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        assert response.status_code == 401

