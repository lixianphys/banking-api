import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from jose import ExpiredSignatureError, JWTError

from simplebank.utils.jwt_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from simplebank.models.models import User
from simplebank.models.schemas import TokenData
from simplebank.tests.conftest import TestingSessionLocal


class TestJWTUtils:
    """Test JWT token utilities"""

    def test_create_access_token(self):
        """Test creating an access token"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(self):
        """Test creating an access token with custom expiration"""
        data = {"sub": "testuser", "user_id": 1}
        custom_expiry = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=custom_expiry)
        
        assert token is not None
        # Verify token contains expiration
        token_data = verify_token(token, token_type="access")
        assert token_data is not None

    def test_create_refresh_token(self):
        """Test creating a refresh token"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_refresh_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_valid_access(self):
        """Test verifying a valid access token"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)
        
        token_data = verify_token(token, token_type="access")
        assert token_data is not None
        assert token_data.username == "testuser"
        assert token_data.user_id == 1

    def test_verify_token_valid_refresh(self):
        """Test verifying a valid refresh token"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_refresh_token(data)
        
        token_data = verify_token(token, token_type="refresh")
        assert token_data is not None
        assert token_data.username == "testuser"
        assert token_data.user_id == 1

    def test_verify_token_wrong_type(self):
        """Test that access token cannot be used as refresh token"""
        data = {"sub": "testuser", "user_id": 1}
        access_token = create_access_token(data)
        
        # Try to verify access token as refresh token
        token_data = verify_token(access_token, token_type="refresh")
        assert token_data is None

    def test_verify_token_invalid(self):
        """Test verifying an invalid token"""
        invalid_token = "invalid.token.here"
        token_data = verify_token(invalid_token, token_type="access")
        assert token_data is None

    def test_verify_token_expired(self):
        """Test verifying an expired token"""
        data = {"sub": "testuser", "user_id": 1}
        # Create token with very short expiration
        expired_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta=expired_delta)
        
        # Wait a bit to ensure expiration
        import time
        time.sleep(0.1)
        
        token_data = verify_token(token, token_type="access")
        assert token_data is None

    def test_verify_token_malformed(self):
        """Test verifying a malformed token"""
        malformed_tokens = [
            "not.a.token",
            "header.payload",  # Missing signature
            "",  # Empty string
            "header.payload.signature.extra"  # Too many parts
        ]
        
        for token in malformed_tokens:
            token_data = verify_token(token, token_type="access")
            assert token_data is None

    def test_get_current_user_valid(self, test_db):
        """Test getting current user with valid token"""
        db = TestingSessionLocal()
        try:
            # Create test user
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create token
            data = {"sub": "testuser", "user_id": user.id}
            token = create_access_token(data)
            
            # Get user from token
            current_user = get_current_user(token, db)
            assert current_user is not None
            assert current_user.id == user.id
            assert current_user.username == "testuser"
        finally:
            db.close()

    def test_get_current_user_invalid_token(self, test_db):
        """Test getting current user with invalid token"""
        db = TestingSessionLocal()
        try:
            invalid_token = "invalid.token"
            current_user = get_current_user(invalid_token, db)
            assert current_user is None
        finally:
            db.close()

    def test_get_current_user_nonexistent(self, test_db):
        """Test getting current user that doesn't exist"""
        db = TestingSessionLocal()
        try:
            # Create token for non-existent user
            data = {"sub": "nonexistent", "user_id": 999}
            token = create_access_token(data)
            
            current_user = get_current_user(token, db)
            assert current_user is None
        finally:
            db.close()

    def test_get_current_user_inactive(self, test_db):
        """Test getting current user that is inactive"""
        db = TestingSessionLocal()
        try:
            # Create inactive user
            user = User(
                username="inactiveuser",
                email="inactive@example.com",
                hashed_password="hashed",
                is_active=False
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create token
            data = {"sub": "inactiveuser", "user_id": user.id}
            token = create_access_token(data)
            
            # Should return None for inactive user
            current_user = get_current_user(token, db)
            assert current_user is None
        finally:
            db.close()

    def test_token_contains_expiration(self):
        """Test that tokens contain expiration information"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)
        
        # Decode without verification to check expiration
        from jose import jwt
        from simplebank.utils.jwt_utils import SECRET_KEY, ALGORITHM
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload
        assert "type" in payload
        assert payload["type"] == "access"

    def test_refresh_token_has_longer_expiry(self):
        """Test that refresh tokens have longer expiration than access tokens"""
        data = {"sub": "testuser", "user_id": 1}
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)
        
        from jose import jwt
        from simplebank.utils.jwt_utils import SECRET_KEY, ALGORITHM
        
        access_payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        refresh_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Refresh token should expire later than access token
        assert refresh_payload["exp"] > access_payload["exp"]

