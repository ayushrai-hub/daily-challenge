"""
Celery configuration for background tasks in the Daily Challenge application.
Uses Redis as the broker and result backend.
"""
from celery import Celery, Task
from typing import Any, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()

# Import the beat schedule
from app.core.celery_beat import beat_schedule

# Create the Celery app
celery_app = Celery(
    "daily_challenge",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.email.send_email",  # Include task modules here
        "app.tasks.email.process_pending_emails",
        "app.tasks.email.send_solution_email",  # Solution email module
        "app.tasks.content_processing.problem_tasks",
        "app.tasks.maintenance.health_check",
        "app.tasks.maintenance.token_cleanup",  # Token cleanup task
        # Daily challenge tasks
        "app.tasks.daily_challenge.schedule_challenges",
        # Add content pipeline modules
        "app.tasks.content_processing.pipeline.content_sources",
        "app.tasks.content_processing.pipeline.ai_processing",
    ],
)

# Define task routing to specific queues
task_routes = {
    # Email tasks go to the emails queue
    'app.tasks.email.*': {'queue': 'emails'},
    'app.tasks.email.send_email.*': {'queue': 'emails'},
    'app.tasks.email.process_pending_emails.*': {'queue': 'emails'},
    
    # Content processing tasks go to the content queue
    'app.tasks.content_processing.*': {'queue': 'content'},
    'app.tasks.content_processing.pipeline.*': {'queue': 'content'},
    'fetch_github_content': {'queue': 'content'},
    'fetch_stackoverflow_content': {'queue': 'content'},
    'fetch_combined_content': {'queue': 'content'},
    'generate_problems_with_ai': {'queue': 'content'},
    'save_problems_to_database': {'queue': 'content'},
    'complete_content_pipeline': {'queue': 'content'},
    
    # Maintenance tasks go to the default queue
    'app.tasks.maintenance.*': {'queue': 'default'},
}

# Configure Celery settings
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Queue settings
    task_default_queue="default",
    task_routes=task_routes,  # Add task routing configuration
    # Task execution settings
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=300,  # 5 minutes
    # Result settings
    result_expires=3600,  # 1 hour
    # Worker settings
    worker_concurrency=4,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=100,
    # Task track started
    task_track_started=True,  # Track when tasks are started for better monitoring
    # Logging settings
    worker_hijack_root_logger=False,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    # Beat schedule
    beat_schedule=beat_schedule,
)

# Optional task base class
class BaseTask(Task):
    """Base class for all Celery tasks in the application."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failure."""
        logger.error(
            f"Task {self.name}[{task_id}] failed: {exc} - args: {args} - kwargs: {kwargs}",
            exc_info=exc
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        """Log task success."""
        logger.debug(
            f"Task {self.name}[{task_id}] succeeded - args: {args} - kwargs: {kwargs} - result: {retval}"
        )
        super().on_success(retval, task_id, args, kwargs)

# Set the default task base class
celery_app.Task = BaseTask

# Function to register content pipeline tasks and schedules
def register_content_pipeline():
    """Register content pipeline tasks and schedule configuration.
    
    Call this function after application initialization to avoid circular imports.
    """
    try:
        # Import content pipeline modules only when needed
        from app.tasks.content_processing.pipeline.scheduler import get_content_pipeline_schedule, register_content_pipeline_routes
        
        # Update beat schedule with content pipeline schedules
        content_schedules = get_content_pipeline_schedule()
        celery_app.conf.beat_schedule.update(content_schedules)
        
        # Add additional task routes
        pipeline_routes = register_content_pipeline_routes()
        celery_app.conf.task_routes.update(pipeline_routes)
        
        logger.info("Content pipeline registered successfully")
    except Exception as e:
        logger.error(f"Error registering content pipeline: {e}")

# Function to get the current Celery app instance
def get_celery_app() -> Celery:
    """Get the Celery application instance."""
    return celery_app

# Run this only when celery_app.py is imported, not when Celery worker loads the app
try:
    # Avoid importing this during worker startup to prevent early imports
    if __name__ != "__mp_main__" and not celery_app.current_worker_task:
        register_content_pipeline()
except (AttributeError, ImportError):
    # Catch exception when running in worker context
    pass
