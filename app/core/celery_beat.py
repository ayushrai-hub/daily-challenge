"""
Celery Beat schedule configuration for Daily Challenge application.
Defines periodic tasks for content generation, delivery, and maintenance.
"""
from celery.schedules import crontab
from app.core.config import settings
from datetime import timedelta

# Define the schedule for periodic tasks
CELERY_BEAT_SCHEDULE = {
    # Daily problem delivery task - runs every day at 8:00 AM UTC
    'schedule-daily-problems': {
        'task': 'app.tasks.daily_challenge.schedule_challenges.schedule_daily_problems',
        'schedule': crontab(hour=8, minute=0),
        'kwargs': {
            'delivery_hour': 8  # Configure delivery hour
        },
        'options': {
            'queue': 'content',
            'expires': 3600,  # 1 hour
        },
    },
    
    # Check for problems delivered ~24 hours ago and schedule solutions
    'schedule-pending-solutions': {
        'task': 'app.tasks.daily_challenge.schedule_challenges.schedule_pending_solutions',
        'schedule': crontab(hour='*', minute=30),  # Run every hour at 30 minutes past
        'options': {
            'queue': 'content',
            'expires': 3600,  # 1 hour
        },
    },
    
    # Weekly content generation - runs every Monday at 2:00 AM UTC
    'generate-weekly-content': {
        'task': 'generate_daily_challenges',
        'schedule': crontab(hour=2, minute=0, day_of_week='monday'),
        'kwargs': {
            'batch_size': 20,
            'difficulty_distribution': {'easy': 0.4, 'medium': 0.4, 'hard': 0.2}
        },
        'options': {
            'queue': 'content',
            'expires': 7200,  # 2 hours
        },
    },
    
    # Daily system health check - runs every day at 0:00 AM UTC
    'daily-system-health': {
        'task': 'app.tasks.maintenance.health_check',
        'schedule': crontab(hour=0, minute=0),
        'options': {
            'queue': 'default',
            'expires': 3600,  # 1 hour
        },
    },
    
    # Every minute check for pending challenge emails
    'process-challenge-email-queue': {
        'task': 'app.tasks.daily_challenge.schedule_challenges.process_challenge_queue',
        'schedule': timedelta(minutes=1),
        'options': {
            'queue': 'emails',
            'expires': 300,  # 5 minutes
        },
    },
    
    # Every minute check for pending general emails (auth, verification, etc.)
    'process-general-email-queue': {
        'task': 'app.tasks.email.process_pending_emails.process_pending_emails',
        'schedule': timedelta(minutes=1),
        'options': {
            'queue': 'emails',
            'expires': 300,  # 5 minutes
        },
    },
    
    # Weekly cleanup of expired verification tokens - runs every Sunday at 3:00 AM UTC
    'cleanup-verification-tokens': {
        'task': 'app.tasks.maintenance.token_cleanup.cleanup_expired_verification_tokens',
        'schedule': crontab(hour=3, minute=0, day_of_week='sunday'),
        'kwargs': {
            'days_threshold': 7  # Delete tokens that are expired and older than 7 days
        },
        'options': {
            'queue': 'maintenance',
            'expires': 3600,  # 1 hour
        },
    },
}

# Export the schedule for use in celery_app.py
beat_schedule = CELERY_BEAT_SCHEDULE
