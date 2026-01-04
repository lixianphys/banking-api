import pytest
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime

from simplebank.models.models import User, Customer, Account
from simplebank.tests.conftest import TestingSessionLocal


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TestUserModel:
    """Test User model creation and relationships"""

    def test_create_user(self, test_db):
        """Test creating a user with all required fields"""
        db = TestingSessionLocal()
        try:
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password_here"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            assert user.id is not None
            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.hashed_password == "hashed_password_here"
            assert user.is_active is True
            assert isinstance(user.created_at, datetime)
        finally:
            db.close()

    def test_user_unique_username(self, test_db):
        """Test that username must be unique"""
        db = TestingSessionLocal()
        try:
            user1 = User(
                username="testuser",
                email="test1@example.com",
                hashed_password="hash1"
            )
            db.add(user1)
            db.commit()

            user2 = User(
                username="testuser",  # Duplicate username
                email="test2@example.com",
                hashed_password="hash2"
            )
            db.add(user2)
            with pytest.raises(Exception):  # Should raise IntegrityError
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_user_unique_email(self, test_db):
        """Test that email must be unique"""
        db = TestingSessionLocal()
        try:
            user1 = User(
                username="user1",
                email="test@example.com",
                hashed_password="hash1"
            )
            db.add(user1)
            db.commit()

            user2 = User(
                username="user2",
                email="test@example.com",  # Duplicate email
                hashed_password="hash2"
            )
            db.add(user2)
            with pytest.raises(Exception):  # Should raise IntegrityError
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_user_is_active_default(self, test_db):
        """Test that is_active defaults to True"""
        db = TestingSessionLocal()
        try:
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hash"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            assert user.is_active is True
        finally:
            db.close()

    def test_user_is_active_can_be_false(self, test_db):
        """Test that is_active can be set to False"""
        db = TestingSessionLocal()
        try:
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hash",
                is_active=False
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            assert user.is_active is False
        finally:
            db.close()

    def test_user_password_hashing(self, test_db):
        """Test that passwords should be hashed (not stored in plain text)"""
        db = TestingSessionLocal()
        try:
            password = "plaintext_password"
            hashed = pwd_context.hash(password)
            
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password=hashed
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Verify password is hashed (not plain text)
            assert user.hashed_password != password
            assert user.hashed_password == hashed
            # Verify we can check the password
            assert pwd_context.verify(password, user.hashed_password)
        finally:
            db.close()

    def test_user_created_at_auto_set(self, test_db):
        """Test that created_at is automatically set"""
        db = TestingSessionLocal()
        try:
            before_creation = datetime.utcnow()
            user = User(
                username="testuser",
                email="test@example.com",
                hashed_password="hash"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            after_creation = datetime.utcnow()

            assert before_creation <= user.created_at <= after_creation
        finally:
            db.close()

