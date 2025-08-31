#!/usr/bin/env python
"""
Script to manually trigger the content pipeline task.
Used for testing the pipeline with proper error handling.
"""
import os
import sys
import time
import traceback

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.logging import setup_logging, get_logger
from app.tasks.content_processing.pipeline.ai_processing import complete_content_pipeline
from app.tasks.content_processing.pipeline.content_sources import _fetch_github_content_sync, _fetch_stackoverflow_content_sync
from app.services.ai_providers.claude_provider import ClaudeProvider
from app.core.config import settings

# Setup logging
setup_logging()
logger = get_logger()

def test_content_pipeline():
    """Test the content pipeline by triggering the Celery task."""
    logger.info("=== Testing Content Pipeline ===")
    
    try:
        # Verify Redis connection for Celery
        from celery.app.control import Inspect
        from app.core.celery_app import celery_app
        
        logger.info(f"Celery broker URL: {celery_app.conf.broker_url}")
        
        inspector = Inspect(app=celery_app)
        active_queues = inspector.active_queues()
        logger.info(f"Active Celery queues: {active_queues}")
    except Exception as e:
        logger.error(f"Error connecting to Celery broker: {str(e)}")
        traceback.print_exc()
        return
    
    try:
        # First, test if we can directly call the component functions
        logger.info("Testing direct function calls...")
        
        # Test GitHub content fetching
        github_content = _fetch_github_content_sync(api_key=None, query_params=None)
        if github_content:
            logger.info(f"Successfully fetched GitHub content: {len(github_content)} items")
        else:
            logger.warning("GitHub content fetch returned empty result")
        
        # Test Stack Overflow content fetching
        stackoverflow_content = _fetch_stackoverflow_content_sync(app_key=None, query_params=None)
        if stackoverflow_content:
            logger.info(f"Successfully fetched Stack Overflow content: {len(stackoverflow_content)} items")
        else:
            logger.warning("Stack Overflow content fetch returned empty result")
        
        # Test Claude provider
        claude_provider = ClaudeProvider()
        logger.info(f"Initialized ClaudeProvider with model: {claude_provider.model}")
        
        # Finally, try to trigger the task
        logger.info("Triggering content pipeline task...")
        
        # Define default parameters for content sources
        github_params = {
            "repo": "microsoft/vscode", 
            "content_type": "code",
            "max_items": 5
        }
        
        stackoverflow_params = {
            "tags": ["python", "fastapi"],
            "content_type": "questions",
            "sort": "votes",
            "max_items": 5
        }
        
        # Trigger the task with explicit parameters
        task = complete_content_pipeline.delay(
            github_params=github_params,
            stackoverflow_params=stackoverflow_params,
            ai_provider="claude",  # Use the Claude provider as configured in .env
            num_problems=1  # Generate one problem for faster testing
        )
        
        logger.info(f"Task ID: {task.id}")
        logger.info("Task triggered successfully. Check Flower dashboard or logs for results.")
        
    except Exception as e:
        logger.error(f"Error testing content pipeline: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    test_content_pipeline()
