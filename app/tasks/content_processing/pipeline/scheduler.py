"""
Scheduling configuration for content pipeline tasks.
"""
# DO NOT import celery_app here to avoid circular imports
from app.core.config import settings
from app.core.logging import get_logger
from datetime import timedelta

logger = get_logger()


# Schedule configuration for the content pipeline
def get_content_pipeline_schedule():
    """
    Get the schedule configuration for content pipeline tasks.
    Should be imported by celery_beat.py to register these schedules.
    
    Returns:
        Dictionary with schedule configurations
    """
    # Default GitHub parameters for scheduled runs
    default_github_params = {
        "repos": [
            {"repo": "microsoft/vscode", "content_type": "code", "max_items": 3},
            {"repo": "fastapi-users/fastapi-users", "content_type": "code", "max_items": 3},
            {"repo": "tiangolo/fastapi", "content_type": "issues", "max_items": 3}
        ],
        "content_type": "code",
        "max_items": 5
    }
    
    # Default Stack Overflow parameters for scheduled runs
    default_stackoverflow_params = {
        "tags": ["python", "fastapi", "sqlalchemy", "celery"],
        "content_type": "questions",
        "sort": "votes",
        "max_items": 5
    }
    
    # Schedule configuration
    content_pipeline_schedule = {
        # Daily task to fetch content and generate problems
        'content-pipeline-daily-run': {
            'task': 'complete_content_pipeline',
            'schedule': timedelta(days=1),
            'kwargs': {
                'github_params': default_github_params,
                'stackoverflow_params': default_stackoverflow_params,
                'ai_provider': settings.DEFAULT_AI_PROVIDER,
                'num_problems': 5,
                'auto_approve': False  # Require human review before publishing
            },
            'options': {
                'queue': 'content',
                'expires': 3600 * 2  # 2 hours
            }
        },
        
        # Weekly task to generate a larger batch of problems
        'content-pipeline-weekly-run': {
            'task': 'complete_content_pipeline',
            'schedule': timedelta(days=7),  # Run once a week
            'kwargs': {
                'github_params': {
                    **default_github_params,
                    'max_items': 10  # Get more content for the weekly run
                },
                'stackoverflow_params': {
                    **default_stackoverflow_params,
                    'max_items': 10,
                    'sort': 'activity'  # Use different sorting for variety
                },
                'ai_provider': settings.DEFAULT_AI_PROVIDER,
                'num_problems': 10,
                'auto_approve': False
            },
            'options': {
                'queue': 'content',
                'expires': 3600 * 4  # 4 hours
            }
        }
    }
    
    return content_pipeline_schedule


# Register task routes for the content pipeline
def register_content_pipeline_routes():
    """Register task routes for content pipeline tasks."""
    content_pipeline_routes = {
        'app.tasks.content_processing.pipeline.content_sources.*': {'queue': 'content'},
        'app.tasks.content_processing.pipeline.ai_processing.*': {'queue': 'content'},
        'fetch_github_content': {'queue': 'content'},
        'fetch_stackoverflow_content': {'queue': 'content'},
        'fetch_combined_content': {'queue': 'content'},
        'generate_problems_with_ai': {'queue': 'content'},
        'save_problems_to_database': {'queue': 'content'},
        'complete_content_pipeline': {'queue': 'content'}
    }
    
    return content_pipeline_routes
