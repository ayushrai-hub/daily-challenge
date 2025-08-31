"""
Content ingestion and AI processing pipeline tasks.
"""

# Explicitly import all task modules to ensure Celery discovers them
# This avoids circular import issues by using shared_task
from app.tasks.content_processing.pipeline import content_sources, ai_processing

# Import specific task functions for easier access
from app.tasks.content_processing.pipeline.content_sources import (
    fetch_github_content,
    fetch_stackoverflow_content,
    fetch_combined_content
)

from app.tasks.content_processing.pipeline.ai_processing import (
    generate_problems_with_ai,
    save_problems_to_database,
    complete_content_pipeline
)
