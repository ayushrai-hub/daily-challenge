"""
Models for tracking email verification metrics.
"""
from sqlalchemy import Column, String, Integer, DateTime, func, Float
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.db.models.base_model import BaseModel


class VerificationMetrics(BaseModel):
    """
    Model for tracking email verification metrics by date.
    
    This tracks daily statistics about verification rates and user behavior.
    """
    __tablename__ = "verification_metrics"

    # Use date as a string in YYYY-MM-DD format as the primary identifier
    date = Column(String, nullable=False, index=True)
    
    # Total counts
    verification_requests_sent = Column(Integer, default=0, nullable=False)
    verification_completed = Column(Integer, default=0, nullable=False)
    verification_expired = Column(Integer, default=0, nullable=False)
    resend_requests = Column(Integer, default=0, nullable=False)
    
    # Time-based metrics (in seconds)
    avg_verification_time = Column(Float, nullable=True)
    median_verification_time = Column(Float, nullable=True)
    min_verification_time = Column(Float, nullable=True)
    max_verification_time = Column(Float, nullable=True)
    
    # Additional fields
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @classmethod
    def get_or_create_for_today(cls, db):
        """Get existing metrics for today or create new entry if not exists."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Try to find existing entry for today
        metrics = db.query(cls).filter(cls.date == today).first()
        
        # Create new entry if none exists
        if not metrics:
            metrics = cls(
                date=today,
                verification_requests_sent=0,
                verification_completed=0,
                verification_expired=0,
                resend_requests=0
            )
            db.add(metrics)
            db.commit()
            db.refresh(metrics)
            
        return metrics
        
    @classmethod
    def get_for_date_range(cls, db, start_date, end_date):
        """Get metrics for a date range.
        
        Args:
            db: Database session
            start_date: Start date (inclusive) in YYYY-MM-DD format
            end_date: End date (inclusive) in YYYY-MM-DD format
            
        Returns:
            List of VerificationMetrics objects within the date range
        """
        return db.query(cls).filter(
            cls.date >= start_date,
            cls.date <= end_date
        ).all()
        
    @classmethod
    def get_aggregate_metrics(cls, db, start_date, end_date):
        """Get aggregate metrics across a date range.
        
        Args:
            db: Database session
            start_date: Start date (inclusive) in YYYY-MM-DD format
            end_date: End date (inclusive) in YYYY-MM-DD format
            
        Returns:
            Dictionary with aggregated metrics
        """
        metrics = cls.get_for_date_range(db, start_date, end_date)
        
        # Initialization with default values
        total_requests_sent = 0
        total_completed = 0
        total_expired = 0
        total_resend_requests = 0
        verification_rate = 0
        avg_times = [m.avg_verification_time for m in metrics if m.avg_verification_time is not None]
        min_times = [m.min_verification_time for m in metrics if m.min_verification_time is not None]
        max_times = [m.max_verification_time for m in metrics if m.max_verification_time is not None]
        
        # Calculate totals
        for m in metrics:
            total_requests_sent += m.verification_requests_sent
            total_completed += m.verification_completed
            total_expired += m.verification_expired
            total_resend_requests += m.resend_requests
        
        # Calculate rate if we have requests
        if total_requests_sent > 0:
            verification_rate = total_completed / total_requests_sent
        
        # Build metrics dictionary
        return {
            'total_requests_sent': total_requests_sent,
            'total_completed': total_completed,
            'total_expired': total_expired,
            'total_resend_requests': total_resend_requests,
            'verification_rate': verification_rate,
            'avg_verification_time': sum(avg_times) / len(avg_times) if avg_times else None,
            'min_verification_time': min(min_times) if min_times else None,
            'max_verification_time': max(max_times) if max_times else None,
            'date_range': f"{start_date} to {end_date}",
            'days_in_range': len(metrics)
        }
        
    def update_verification_sent(self, db):
        """Increment the verification_requests_sent counter"""
        self.verification_requests_sent += 1
        db.add(self)
        db.commit()
        
    def update_verification_completed(self, db, verification_time_seconds=None):
        """
        Increment the verification_completed counter and update time metrics
        
        Args:
            db: Database session
            verification_time_seconds: How long verification took in seconds
        """
        self.verification_completed += 1
        
        # Update time metrics if time data is provided
        if verification_time_seconds is not None:
            # If this is the first verification, initialize metrics
            if self.avg_verification_time is None:
                self.avg_verification_time = verification_time_seconds
                self.median_verification_time = verification_time_seconds
                self.min_verification_time = verification_time_seconds
                self.max_verification_time = verification_time_seconds
            else:
                # Update running average
                total_time = self.avg_verification_time * (self.verification_completed - 1)
                self.avg_verification_time = (total_time + verification_time_seconds) / self.verification_completed
                
                # Update min/max
                if verification_time_seconds < self.min_verification_time:
                    self.min_verification_time = verification_time_seconds
                if verification_time_seconds > self.max_verification_time:
                    self.max_verification_time = verification_time_seconds
                    
                # Note: Proper median calculation would require storing all values
                # This is a simplification for demonstration
                self.median_verification_time = self.avg_verification_time
        
        db.add(self)
        db.commit()
        
    def update_verification_expired(self, db):
        """Increment the verification_expired counter"""
        self.verification_expired += 1
        db.add(self)
        db.commit()
        
    def update_resend_requests(self, db):
        """Increment the resend_requests counter"""
        self.resend_requests += 1
        db.add(self)
        db.commit()
