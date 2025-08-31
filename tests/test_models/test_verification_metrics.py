"""
Tests for the VerificationMetrics model.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from app.db.models.verification_metrics import VerificationMetrics


class TestVerificationMetrics:
    """Test class for verification metrics model."""

    def test_get_or_create_for_today_new(self, db_session):
        """Test creating new metrics for today when none exist."""
        # Arrange - set fixed date for testing
        with patch('app.db.models.verification_metrics.datetime') as mock_datetime:
            test_date = datetime(2025, 5, 8)
            formatted_date = test_date.strftime("%Y-%m-%d")
            mock_datetime.utcnow.return_value = test_date
            
            # Act
            metrics = VerificationMetrics.get_or_create_for_today(db=db_session)
            
            # Assert
            assert metrics is not None
            assert metrics.date == formatted_date
            assert metrics.verification_requests_sent == 0
            assert metrics.verification_completed == 0
            assert metrics.verification_expired == 0
            assert metrics.resend_requests == 0
            
            # Verify it was saved to database
            db_metrics = db_session.query(VerificationMetrics).filter(
                VerificationMetrics.date == formatted_date
            ).first()
            assert db_metrics is not None
            assert db_metrics.id == metrics.id

    def test_get_or_create_for_today_existing(self, db_session):
        """Test getting existing metrics for today."""
        # Arrange - set fixed date and create metrics
        with patch('app.db.models.verification_metrics.datetime') as mock_datetime:
            test_date = datetime(2025, 5, 8)
            formatted_date = test_date.strftime("%Y-%m-%d")
            mock_datetime.utcnow.return_value = test_date
            
            # Create initial metrics
            first_metrics = VerificationMetrics.get_or_create_for_today(db=db_session)
            first_metrics.verification_requests_sent = 5
            db_session.commit()
            
            # Act - call again to get existing metrics
            second_metrics = VerificationMetrics.get_or_create_for_today(db=db_session)
            
            # Assert
            assert second_metrics is not None
            assert second_metrics.id == first_metrics.id
            assert second_metrics.date == formatted_date
            assert second_metrics.verification_requests_sent == 5

    def test_increment_verification_sent(self, db_session):
        """Test incrementing the verification_requests_sent counter."""
        # Arrange
        metrics = VerificationMetrics.get_or_create_for_today(db=db_session)
        initial_count = metrics.verification_requests_sent
        
        # Act
        metrics.update_verification_sent(db=db_session)
        
        # Assert
        assert metrics.verification_requests_sent == initial_count + 1
        
        # Verify in database - use Session.get() for SQLAlchemy 2.0 compatibility
        db_metrics = db_session.get(VerificationMetrics, metrics.id)
        assert db_metrics.verification_requests_sent == initial_count + 1

    def test_increment_verification_completed(self, db_session):
        """Test incrementing the verification_completed counter."""
        # Arrange
        metrics = VerificationMetrics.get_or_create_for_today(db=db_session)
        initial_count = metrics.verification_completed
        verification_time = 120.5  # seconds
        
        # Act
        metrics.update_verification_completed(db=db_session, verification_time_seconds=verification_time)
        
        # Assert
        assert metrics.verification_completed == initial_count + 1
        assert metrics.avg_verification_time is not None
        assert metrics.min_verification_time is not None
        assert metrics.max_verification_time is not None
        
        # Check that times were properly set for first verification
        assert metrics.avg_verification_time == verification_time
        assert metrics.min_verification_time == verification_time
        assert metrics.max_verification_time == verification_time
        
        # Verify in database - use Session.get() for SQLAlchemy 2.0 compatibility
        db_metrics = db_session.get(VerificationMetrics, metrics.id)
        assert db_metrics.verification_completed == initial_count + 1

    def test_increment_verification_completed_multiple(self, db_session):
        """Test incrementing verification_completed multiple times to check averages."""
        # Arrange
        metrics = VerificationMetrics.get_or_create_for_today(db=db_session)
        
        # Act - add first verification time
        first_time = 60.0
        metrics.update_verification_completed(db=db_session, verification_time_seconds=first_time)
        
        # Add second verification time
        second_time = 120.0
        metrics.update_verification_completed(db=db_session, verification_time_seconds=second_time)
        
        # Assert
        assert metrics.verification_completed == 2
        assert metrics.avg_verification_time == 90.0  # (60 + 120) / 2
        assert metrics.min_verification_time == 60.0
        assert metrics.max_verification_time == 120.0

    def test_increment_verification_expired(self, db_session):
        """Test incrementing the verification_expired counter."""
        # Arrange
        metrics = VerificationMetrics.get_or_create_for_today(db=db_session)
        initial_count = metrics.verification_expired
        
        # Act
        metrics.update_verification_expired(db=db_session)
        
        # Assert
        assert metrics.verification_expired == initial_count + 1
        
        # Verify in database - use Session.get() for SQLAlchemy 2.0 compatibility
        db_metrics = db_session.get(VerificationMetrics, metrics.id)
        assert db_metrics.verification_expired == initial_count + 1

    def test_increment_resend_requests(self, db_session):
        """Test incrementing the resend_requests counter."""
        # Arrange
        metrics = VerificationMetrics.get_or_create_for_today(db=db_session)
        initial_count = metrics.resend_requests
        
        # Act
        metrics.update_resend_requests(db=db_session)
        
        # Assert
        assert metrics.resend_requests == initial_count + 1
        
        # Verify in database - use Session.get() for SQLAlchemy 2.0 compatibility
        db_metrics = db_session.get(VerificationMetrics, metrics.id)
        assert db_metrics.resend_requests == initial_count + 1

    def test_get_for_date_range(self, db_session):
        """Test getting metrics for a date range."""
        # Create a series of metrics for different dates
        dates = [
            "2025-05-01",
            "2025-05-02",
            "2025-05-03",
            "2025-05-04",
            "2025-05-05"
        ]
        
        # Create metrics for each date
        for date in dates:
            metrics = VerificationMetrics(
                date=date,
                verification_requests_sent=10,
                verification_completed=7,
                verification_expired=2,
                resend_requests=1
            )
            db_session.add(metrics)
        
        db_session.commit()
        
        # Test getting metrics for a specific date range
        start_date = "2025-05-02"
        end_date = "2025-05-04"
        
        # Call the method
        result = VerificationMetrics.get_for_date_range(db_session, start_date, end_date)
        
        # Assert
        assert len(result) == 3  # Should return 3 days of metrics (02, 03, 04)
        
        # Verify all dates are within range
        for metrics in result:
            assert metrics.date >= start_date
            assert metrics.date <= end_date

    def test_get_aggregate_metrics(self, db_session):
        """Test getting aggregate metrics across a date range."""
        # Create a series of metrics for different dates with varying values
        test_data = [
            # date, sent, completed, expired, resend, avg_time, min_time, max_time
            ("2025-06-01", 100, 70, 20, 10, 45.0, 30.0, 60.0),
            ("2025-06-02", 80, 60, 15, 5, 50.0, 35.0, 65.0),
            ("2025-06-03", 120, 90, 25, 5, 40.0, 25.0, 55.0)
        ]
        
        # Create metrics for each date
        for date, sent, completed, expired, resend, avg_time, min_time, max_time in test_data:
            metrics = VerificationMetrics(
                date=date,
                verification_requests_sent=sent,
                verification_completed=completed,
                verification_expired=expired,
                resend_requests=resend,
                avg_verification_time=avg_time,
                min_verification_time=min_time,
                max_verification_time=max_time
            )
            db_session.add(metrics)
        
        db_session.commit()
        
        # Test getting aggregated metrics for this date range
        start_date = "2025-06-01"
        end_date = "2025-06-03"
        
        # Call the method
        result = VerificationMetrics.get_aggregate_metrics(db_session, start_date, end_date)
        
        # Assert the totals match our test data
        assert result["total_requests_sent"] == 300  # 100 + 80 + 120
        assert result["total_completed"] == 220  # 70 + 60 + 90
        assert result["total_expired"] == 60  # 20 + 15 + 25
        assert result["total_resend_requests"] == 20  # 10 + 5 + 5
        
        # Check the calculated metrics
        assert result["verification_rate"] == 220/300  # Completion rate
        assert result["avg_verification_time"] == 45.0  # Average of 45, 50, 40
        assert result["min_verification_time"] == 25.0  # Minimum of all min times
        assert result["max_verification_time"] == 65.0  # Maximum of all max times
        
        # Check date range and number of days
        assert result["date_range"] == "2025-06-01 to 2025-06-03"
        assert result["days_in_range"] == 3
