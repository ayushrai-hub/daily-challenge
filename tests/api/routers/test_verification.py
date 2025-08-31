"""
Tests for the email verification endpoints.
"""
"""Tests for the email verification endpoints using dependency overrides."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import deps
from app.api.routers import auth
from app.main import app
from app.db.models.verification_token import VerificationToken
from app.db.models.verification_metrics import VerificationMetrics
from app.db.models.user import User
from app.core.config import settings
from app.repositories.user import UserRepository


class TestVerificationEndpoints:
    """Test class for email verification endpoints using dependency overrides."""
    
    @pytest.fixture
    def unverified_user(self):
        """Create a mock unverified user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "unverified@example.com"
        user.full_name = "Unverified User"
        user.is_email_verified = False
        user.is_active = True
        user.last_login = datetime.now(timezone.utc) - timedelta(days=1)
        return user
        
    @pytest.fixture
    def verified_user(self):
        """Create a mock verified user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "verified@example.com"
        user.full_name = "Verified User"
        user.is_email_verified = True
        user.is_active = True
        user.last_login = datetime.now(timezone.utc) - timedelta(days=1)
        return user
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()
        return db
    
    @pytest.fixture
    def disable_rate_limit(self, monkeypatch):
        """Disable rate limiting for tests."""
        # Create a dummy decorator that does nothing
        def mock_rate_limit(limit_value):
            def decorator(func):
                return func
            return decorator
            
        # Patch the rate_limit decorator with our mock
        monkeypatch.setattr("app.core.rate_limiter.rate_limit", mock_rate_limit)
        
    @pytest.fixture
    def test_client(self, unverified_user, verified_user, mock_db, disable_rate_limit):
        """Create a test client with dependency overrides."""
        # Create a copy of the app to avoid affecting other tests
        test_app = FastAPI()
        
        # Include the router with the /api prefix to match the main application
        test_app.include_router(auth.router, prefix="/api")
        
        # Define dependency overrides
        def get_db_override():
            return mock_db
        
        def get_current_user_override():
            return unverified_user
        
        # Apply dependency overrides
        test_app.dependency_overrides[deps.get_db] = get_db_override
        test_app.dependency_overrides[deps.get_current_user] = get_current_user_override
        
        # Create and return the test client
        with TestClient(test_app) as client:
            yield client, unverified_user, verified_user, mock_db
            
        # Clear dependency overrides after test
        test_app.dependency_overrides = {}

    def test_verify_email_success(self, test_client):
        """Test successful email verification using mocked dependencies."""
        client, user, _, mock_db = test_client
        
        # Setup VerificationToken.validate_token mock
        user_id_str = str(user.id)
        with patch.object(VerificationToken, 'validate_token', return_value=user_id_str):
            # Setup VerificationToken.mark_as_used mock
            mock_token = MagicMock()
            mock_token.is_used = True
            mock_token.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
            
            with patch.object(VerificationToken, 'mark_as_used', return_value=mock_token):
                # Setup VerificationMetrics mock
                mock_metrics = MagicMock()
                with patch.object(VerificationMetrics, 'get_or_create_for_today', return_value=mock_metrics):
                    with patch.object(VerificationMetrics, 'update_verification_completed'):
                        with patch.object(UserRepository, 'get', return_value=user):
                            # Act
                            response = client.post(f"/api/auth/verify-email/test_token")
        
        # Verify response
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["user_id"] == user_id_str
        assert result["email"] == user.email
        assert result["status"] == "verified"
        
        # Verify user was updated
        assert user.is_email_verified is True
        mock_db.add.assert_called_with(user)
        mock_db.commit.assert_called_once()

    def test_verify_email_invalid_token(self, test_client):
        """Test verification with an invalid token."""
        client, _, _, _ = test_client
        
        # Mock VerificationToken.validate_token to return None (invalid token)
        with patch.object(VerificationToken, 'validate_token', return_value=None):
            # Act
            response = client.post("/api/auth/verify-email/invalid_token")
        
        # Verify response
        assert response.status_code == 400
        error_detail = response.json().get("detail", "")
        assert "Invalid or expired verification token" in error_detail

    def test_verify_email_expired_token(self, test_client):
        """Test verification with an expired token."""
        client, _, _, _ = test_client
        
        # Mock VerificationToken.validate_token to raise an exception for expired token
        with patch.object(VerificationToken, 'validate_token', side_effect=HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "http_400", "message": "Token has expired", "details": None}
        )):
            # Act
            response = client.post("/api/auth/verify-email/expired_token")
        
        # Verify response
        assert response.status_code == 400
        detail = response.json().get("detail", {})
        # Handle both string and dict response formats
        if isinstance(detail, dict):
            assert "expired" in detail.get("message", "").lower()
        else:
            assert "expired" in str(detail).lower()

    def test_verify_email_already_used_token(self, test_client):
        """Test verification with a token that has already been used."""
        client, _, _, _ = test_client
        
        # Mock VerificationToken.validate_token to raise an exception for used token
        with patch.object(VerificationToken, 'validate_token', side_effect=HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "http_400", "message": "Token has already been used", "details": None}
        )):
            # Act
            response = client.post("/api/auth/verify-email/used_token")
        
        # Verify response
        assert response.status_code == 400
        detail = response.json().get("detail", {})
        # Handle both string and dict response formats
        if isinstance(detail, dict):
            assert "used" in detail.get("message", "").lower()
        else:
            assert "used" in str(detail).lower()

    def test_resend_verification_success(self, test_client):
        """Test successfully resending verification email."""
        client, user, _, mock_db = test_client
        
        # Ensure verify_check_recent_token returns None (no cooldown)
        with patch.object(VerificationToken, 'check_recent_token', return_value=None):
            # Mock token creation
            mock_token = MagicMock()
            mock_token.token = "new_verification_token"
            with patch.object(VerificationToken, 'create_token', return_value=mock_token):
                # Mock metrics
                mock_metrics = MagicMock()
                with patch.object(VerificationMetrics, 'get_or_create_for_today', return_value=mock_metrics):
                    with patch.object(VerificationMetrics, 'update_resend_requests'):
                        with patch.object(VerificationMetrics, 'update_verification_sent'):
                            # Mock email sending (patch the background task system)
                            with patch('app.tasks.email.send_email.send_verification_email') as mock_send_email:
                                # Act
                                response = client.post("/api/auth/resend-verification")
        
        # Verify response
        assert response.status_code == 200
        result = response.json()
        assert "message" in result and "sent successfully" in result["message"]
        assert result["email"] == user.email
        assert result["status"] == "pending"

    def test_resend_verification_already_verified(self, test_client):
        """Test resending verification when already verified."""
        client, _, verified_user, _ = test_client
        
        # Override the dependency to return a verified user
        app = client.app
        app.dependency_overrides[deps.get_current_user] = lambda: verified_user
        
        # Act
        response = client.post("/api/auth/resend-verification")
        
        # Verify response
        assert response.status_code == 400
        error_detail = response.json().get("detail", "")
        assert "Email already verified" in error_detail

    def test_resend_verification_cooldown(self, test_client):
        """Test resending verification within cooldown period."""
        client, user, _, mock_db = test_client
        
        # Create a recent token to trigger cooldown
        mock_token = MagicMock()
        mock_token.created_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        mock_token.user_id = str(user.id)
        mock_token.token_type = "email_verification"
        mock_token.is_used = False
        
        # Mock token check to return the recent token (triggering cooldown)
        with patch.object(VerificationToken, 'check_recent_token', return_value=mock_token):
            # Mock metrics
            mock_metrics = MagicMock()
            with patch.object(VerificationMetrics, 'get_or_create_for_today', return_value=mock_metrics):
                with patch.object(VerificationMetrics, 'update_resend_requests'):
                    # Act
                    response = client.post("/api/auth/resend-verification")
        
        # Verify response
        assert response.status_code == 429
        detail = response.json().get("detail", "")
        assert "wait" in detail.lower()

    # The bypass mode tests are using specific application settings and should be tested separately
    # with proper integration tests that include the router for users/me/profile.
