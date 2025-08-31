"""
Tests for the VerificationToken model.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.db.models.verification_token import VerificationToken
from app.db.models.user import User


class TestVerificationToken:
    """Test class for verification token model."""

    def test_create_token(self, db_session):
        """Test creating a verification token."""
        # Arrange
        user = db_session.query(User).filter(User.email == "user@example.com").first()
        assert user is not None, "Test user not found"
        
        # Act
        token = VerificationToken.create_token(
            db=db_session,
            user_id=user.id
        )
        
        # Assert
        assert token is not None
        assert token.user_id == user.id
        assert token.token is not None
        assert len(token.token) > 0
        assert token.is_used is False
        assert token.token_type == "email_verification"
        
        # Convert to naive datetime for comparison if needed
        expires_at = token.expires_at
        if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
            
        assert expires_at > datetime.utcnow()

    def test_create_token_with_custom_expiration(self, db_session):
        """Test creating a token with custom expiration."""
        # Arrange
        user = db_session.query(User).filter(User.email == "user@example.com").first()
        assert user is not None, "Test user not found"
        custom_hours = 48
        
        # Act
        token = VerificationToken.create_token(
            db=db_session,
            user_id=user.id,
            expiration_hours=custom_hours
        )
        
        # Assert
        # Convert to naive datetime for comparison if needed
        expires_at = token.expires_at
        if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
            
        now = datetime.utcnow()
        expected_min_expiration = now + timedelta(hours=custom_hours - 1)  # Allow 1 hour margin
        expected_max_expiration = now + timedelta(hours=custom_hours + 1)  # Allow 1 hour margin
        assert expires_at > expected_min_expiration
        assert expires_at < expected_max_expiration

    def test_create_token_with_custom_type(self, db_session):
        """Test creating a token with custom type."""
        # Arrange
        user = db_session.query(User).filter(User.email == "user@example.com").first()
        assert user is not None, "Test user not found"
        custom_type = "password_reset"
        
        # Act
        token = VerificationToken.create_token(
            db=db_session,
            user_id=user.id,
            token_type=custom_type
        )
        
        # Assert
        assert token.token_type == custom_type

    def test_validate_token_valid(self, db_session):
        """Test validating a valid token."""
        # Arrange
        user = db_session.query(User).filter(User.email == "user@example.com").first()
        assert user is not None, "Test user not found"
        token = VerificationToken.create_token(
            db=db_session,
            user_id=user.id
        )
        
        # Act
        result = VerificationToken.validate_token(
            db=db_session,
            token_value=token.token
        )
        
        # Assert
        assert result == user.id

    def test_validate_token_expired(self, db_session):
        """Test validating an expired token."""
        # Arrange
        user = db_session.query(User).filter(User.email == "user@example.com").first()
        assert user is not None, "Test user not found"
        
        # Create a token directly without mocking datetime
        # Make sure it's already expired when we create it
        token = VerificationToken(
            user_id=user.id,
            token="expired_token_test",
            token_type="email_verification",
            is_used=False,
            # Set an expiration date in the past
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        db_session.add(token)
        db_session.commit()
        
        # Act - validate the token which should fail due to expiration
        result = VerificationToken.validate_token(
            db=db_session,
            token_value=token.token
        )
        
        # Assert - validation should fail (return None) because token is expired
        assert result is None

    def test_validate_token_used(self, db_session):
        """Test validating a token that has already been used."""
        # Arrange
        user = db_session.query(User).filter(User.email == "user@example.com").first()
        assert user is not None, "Test user not found"
        token = VerificationToken.create_token(
            db=db_session,
            user_id=user.id
        )
        
        # Mark token as used
        token.is_used = True
        db_session.commit()
        
        # Act
        result = VerificationToken.validate_token(
            db=db_session,
            token_value=token.token
        )
        
        # Assert
        assert result is None

    def test_validate_token_wrong_type(self, db_session):
        """Test validating a token with wrong type."""
        # Arrange
        user = db_session.query(User).filter(User.email == "user@example.com").first()
        assert user is not None, "Test user not found"
        token = VerificationToken.create_token(
            db=db_session,
            user_id=user.id,
            token_type="password_reset"
        )
        
        # Act
        result = VerificationToken.validate_token(
            db=db_session,
            token_value=token.token,
            token_type="email_verification"  # Different type
        )
        
        # Assert
        assert result is None

    def test_validate_token_nonexistent(self, db_session):
        """Test validating a token that doesn't exist."""
        # Act
        result = VerificationToken.validate_token(
            db=db_session,
            token_value="non_existent_token"
        )
        
        # Assert
        assert result is None

    def test_mark_as_used(self, db_session):
        """Test marking a token as used."""
        # Arrange
        user = db_session.query(User).filter(User.email == "user@example.com").first()
        assert user is not None, "Test user not found"
        token = VerificationToken.create_token(
            db=db_session,
            user_id=user.id
        )
        
        # Act
        result = VerificationToken.mark_as_used(
            db=db_session,
            token_value=token.token
        )
        
        # Assert
        assert result is not None
        assert result.is_used is True
        
        # Verify in database
        db_token = db_session.query(VerificationToken).filter(
            VerificationToken.token == token.token
        ).first()
        assert db_token.is_used is True

    def test_mark_as_used_nonexistent(self, db_session):
        """Test marking a non-existent token as used."""
        # Act
        result = VerificationToken.mark_as_used(
            db=db_session,
            token_value="non_existent_token"
        )
        
        # Assert
        assert result is None

    def test_check_recent_token_true(self, db_session):
        """Test checking for a recent token when one exists."""
        # Arrange
        user = db_session.query(User).filter(User.email == "user@example.com").first()
        assert user is not None, "Test user not found"
        token = VerificationToken.create_token(
            db=db_session,
            user_id=user.id
        )
        
        # Act
        result = VerificationToken.check_recent_token(
            db=db_session,
            user_id=user.id,
            minutes=60  # Generous window to avoid timing issues
        )
        
        # Assert
        # Some implementations return the token object, others return True
        assert result is not None

    def test_check_recent_token_false(self, db_session):
        """Test checking for a recent token when none exists."""
        # Arrange
        user = db_session.query(User).filter(User.email == "admin2@example.com").first()
        assert user is not None, "Test user not found"
        
        # Act
        result = VerificationToken.check_recent_token(
            db=db_session,
            user_id=user.id
        )
        
        # Assert
        # This method may return False or None depending on implementation
        assert not result

    def test_check_recent_token_old(self, db_session):
        """Test checking for a recent token when only old ones exist."""
        # Arrange
        user = db_session.query(User).filter(User.email == "admin@example.com").first()
        assert user is not None, "Test user not found"
        
        # Skip this test and use an alternative implementation that doesn't rely on patching datetime
        # Let's verify behavior by directly controlling what's in the database
        
        # First make sure there are no recent tokens
        cutoff_time = datetime.utcnow() - timedelta(minutes=6)  # More than 5 minutes ago
        
        # Delete any recent tokens for this user to ensure clean test state
        recent_tokens = db_session.query(VerificationToken).filter(
            VerificationToken.user_id == user.id,
            VerificationToken.created_at > cutoff_time
        ).all()
        
        for token in recent_tokens:
            db_session.delete(token)
        
        # Create an old token (outside the cooldown window)
        token = VerificationToken(
            user_id=user.id,
            token="old_token_test",
            token_type="email_verification",
            is_used=False,
            created_at=cutoff_time - timedelta(minutes=5),  # 11 minutes ago
            expires_at=datetime.utcnow() + timedelta(hours=24)  # Valid expiration
        )
        db_session.add(token)
        db_session.commit()
        
        # Act - check for tokens within last 5 minutes
        result = VerificationToken.check_recent_token(
            db=db_session,
            user_id=user.id,
            minutes=5  # 5 minute cooldown
        )
        
        # Assert - we expect no recent tokens to be found
        assert not result  # Should be False or None since our token is outside the window
