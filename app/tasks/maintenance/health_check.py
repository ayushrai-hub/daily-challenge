"""
System health monitoring tasks for the Daily Challenge application.
"""
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from sqlalchemy import text
from app.db.session import SessionLocal
import redis
import time
from typing import Dict, Any

logger = get_logger()

@celery_app.task(name="app.tasks.maintenance.health_check", queue="default")
def health_check() -> Dict[str, Any]:
    """
    Check the health of various system components.
    
    Returns:
        Dictionary with health status of each component
    """
    logger.info("Running system health check")
    
    results = {
        "timestamp": time.time(),
        "components": {},
        "overall_status": "healthy"
    }
    
    # Check database connectivity
    try:
        with SessionLocal() as db:
            # Simple query to verify database connection
            db.execute(text("SELECT 1"))
        results["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        results["components"]["database"] = {
            "status": "unhealthy", 
            "error": str(e)
        }
        results["overall_status"] = "degraded"
    
    # Check Redis connectivity
    try:
        from app.core.config import settings
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            socket_connect_timeout=1,
        )
        redis_client.ping()
        results["components"]["redis"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        results["components"]["redis"] = {
            "status": "unhealthy", 
            "error": str(e)
        }
        results["overall_status"] = "degraded"
    
    # Check content inventory
    try:
        with SessionLocal() as db:
            # This would be a real query in production:
            # problem_count = db.query(Problem).filter(Problem.status == "approved").count()
            # For now, we'll simulate this
            problem_count = 100  # Placeholder value
            
            if problem_count < 50:  # Threshold for warning
                results["components"]["content_inventory"] = {
                    "status": "warning",
                    "count": problem_count,
                    "message": "Content inventory is running low"
                }
                if results["overall_status"] == "healthy":
                    results["overall_status"] = "warning"
            else:
                results["components"]["content_inventory"] = {
                    "status": "healthy", 
                    "count": problem_count
                }
    except Exception as e:
        logger.error(f"Content inventory check failed: {str(e)}")
        results["components"]["content_inventory"] = {
            "status": "unknown", 
            "error": str(e)
        }
    
    # Log the overall health status
    if results["overall_status"] != "healthy":
        logger.warning(
            f"System health check complete: {results['overall_status']}",
            extra={"components": results["components"]}
        )
    else:
        logger.info("System health check complete: healthy")
    
    return results
