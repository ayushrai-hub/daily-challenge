"""
Background task scheduler for periodic maintenance tasks.

This module provides a scheduler for running maintenance tasks periodically,
such as tag normalization, cleanup of stale data, etc.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.session import get_db
from app.services.tag_mapper import get_tag_mapper
from app.core.logging import get_logger

# Use the standardized logging system
logger = get_logger()

def tag_maintenance_job():
    """
    Scheduled job to perform maintenance on tags:
    1. Merge duplicate tags
    2. Fix missing parent-child relationships
    3. Normalize tag names
    """
    logger.info(f"Starting scheduled tag maintenance job at {datetime.now()}")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get tag mapper service
        tag_mapper = get_tag_mapper(db)
        
        # Merge duplicate tags
        merge_stats = tag_mapper.merge_duplicate_tags()
        logger.info(f"Tag merge results: {merge_stats}")
        
        # Commit changes
        db.commit()
        logger.info("Tag maintenance completed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Error in tag maintenance job: {str(e)}")
    finally:
        db.close()

def setup_scheduler():
    """
    Set up and start the background scheduler for periodic tasks.
    
    Returns:
        BackgroundScheduler: The initialized scheduler instance
    """
    scheduler = BackgroundScheduler()
    
    # Run tag maintenance daily at 3:00 AM
    scheduler.add_job(
        tag_maintenance_job,
        CronTrigger(hour=3, minute=0),
        id='tag_maintenance_job',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("Background scheduler started with tag maintenance job")
    
    return scheduler
