"""
Tests for the token cleanup Celery task.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from app.db.models.verification_token import VerificationToken
from app.db.models.verification_metrics import VerificationMetrics
from app.tasks.maintenance.token_cleanup import cleanup_expired_verification_tokens


class TestTokenCleanupTask:
    """Test class for token cleanup task."""
    
    def setup_method(self, method):
        """Setup test data before each test method."""
        # Get a valid user ID from the test database for our tests
        from app.db.models.user import User
        from sqlalchemy.orm import Session
        from app.db.database import SessionLocal
        
        # Create a session and get a valid user ID
        db_session = SessionLocal()
        try:
            user = db_session.query(User).filter(User.email == "user@example.com").first()
            if not user:
                # Fallback to admin if user doesn't exist
                user = db_session.query(User).filter(User.email == "admin@example.com").first()
            
            assert user is not None, "Test user not found. Make sure the test database is properly set up."
            self.test_user_id = user.id
        finally:
            db_session.close()

    def test_cleanup_expired_tokens(self, db_session):
        """Test that expired verification tokens are deleted correctly."""
        # Arrange
        user_id = self.test_user_id
        
        # Create an expired token
        expired_token = VerificationToken(
            user_id=user_id,
            token="expired_token",
            expires_at=datetime.utcnow() - timedelta(hours=24),
            token_type="email_verification",
            is_used=False
        )
        
        # Create a valid token (should not be deleted)
        valid_token = VerificationToken(
            user_id=user_id,
            token="valid_token",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            token_type="email_verification",
            is_used=False
        )
        
        # Create a used token (even though it's valid, it should be deleted if old enough)
        used_token = VerificationToken(
            user_id=user_id,
            token="used_token",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            token_type="email_verification",
            is_used=True,
            created_at=datetime.utcnow() - timedelta(days=8)  # Older than the 7-day threshold
        )
        
        # Setup mock database session
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [expired_token, used_token]
        mock_session.commit = MagicMock()
        
        # Act
        with patch('app.tasks.maintenance.token_cleanup.SessionLocal') as mock_session_local:
            mock_session_local.return_value = mock_session
            
            # Call the function
            result = cleanup_expired_verification_tokens()
            
        # Assert
        assert result['success'] is True
        assert result['deleted_count'] == 2  # Two tokens should be deleted
        assert mock_session.execute.called
        assert mock_session.commit.called
        
    def test_metrics_updated_when_cleaning_tokens(self, db_session):
        """Test that verification metrics are updated when cleaning tokens."""
        from app.db.models.user import User
        from datetime import datetime, timedelta, timezone
        
        # Get an existing user ID from the database
        user = db_session.query(User).filter(User.email == "user@example.com").first()
        assert user is not None, "Test user not found. Make sure the test database is properly set up."
        user_id = user.id
        
        # Set a fixed date for the test to ensure tokens are properly identified
        now = datetime.now(timezone.utc)
        past_date = now - timedelta(days=30)  # Create an old token to ensure it's caught by the cleanup
        
        # Create tokens that are both EXPIRED and OLD enough to be cleaned up
        expired_token1 = VerificationToken(
            user_id=user_id,
            token="expired_token_test_1",
            expires_at=past_date,  # Already expired
            token_type="email_verification",
            is_used=False,
            created_at=past_date  # Old enough to be picked up by cleanup
        )
        
        expired_token2 = VerificationToken(
            user_id=user_id,
            token="expired_token_test_2",
            expires_at=past_date,  # Already expired
            token_type="email_verification",
            is_used=False,
            created_at=past_date  # Old enough to be picked up by cleanup
        )
        
        # Also create a token that's USED and OLD enough to be cleaned up
        used_token = VerificationToken(
            user_id=user_id,
            token="used_token_test",
            expires_at=now + timedelta(days=1),  # Not expired
            token_type="email_verification",
            is_used=True,  # But it's used, so should be cleaned up
            created_at=past_date  # And old enough to be picked up by cleanup
        )
        
        # Create initial metrics record for today
        today = now.strftime("%Y-%m-%d")
        # Ensure no duplicate metrics exist for today
        db_session.query(VerificationMetrics).filter(VerificationMetrics.date == today).delete()
        db_session.commit()
        metrics = VerificationMetrics(
            date=today,
            verification_requests_sent=5,
            verification_completed=3,
            verification_expired=0,  # Start with 0 expired
            resend_requests=1
        )
        
        # Add everything to the database
        db_session.add(expired_token1)
        db_session.add(expired_token2)
        db_session.add(used_token)
        db_session.add(metrics)
        db_session.commit()
        
        # Now run the cleanup task with a 7-day threshold (tokens older than 7 days will be deleted)
        with patch('app.tasks.maintenance.token_cleanup.SessionLocal') as mock_session_local:
            mock_session_local.return_value = db_session
            result = cleanup_expired_verification_tokens(days_threshold=7)
        
        # Query directly to get the updated metrics
        updated_metrics = db_session.query(VerificationMetrics).filter(
            VerificationMetrics.date == today
        ).first()
        
        # Assert the expected results
        assert result["success"] is True
        assert result["deleted_count"] == 3  # Should delete all 3 tokens
        assert result["metrics_updated"] is True
        # Metrics should have been updated by the cleanup task to track the 3 expired tokens
        assert updated_metrics.verification_expired == 3
        
    def test_scheduled_task_configuration(self):
        """Test that the task is properly configured in Celery Beat schedule."""
        from app.core.celery_beat import beat_schedule
        
        # Check that our task is in the beat schedule
        assert 'cleanup-verification-tokens' in beat_schedule
        
        task_config = beat_schedule['cleanup-verification-tokens']
        assert task_config['task'] == 'app.tasks.maintenance.token_cleanup.cleanup_expired_verification_tokens'
        
        # Check that task is scheduled to run on Sunday (hour=3, minute=0)
        # The crontab's string representation will tell us when it runs
        crontab_str = str(task_config['schedule'])
        assert "sunday" in crontab_str.lower()
        assert "3" in crontab_str  # Should run at 3 AM
