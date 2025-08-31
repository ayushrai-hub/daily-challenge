from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api import deps
from app.core.config import settings

router = APIRouter(tags=["health"])

@router.get("/health", summary="Health Check")
async def health_check():
    """
    Simple health check endpoint to verify the API is running.
    """
    return {"status": "ok"}

@router.get("/health/detailed", summary="Detailed Health Check", tags=["health"])
async def detailed_health_check(db: Session = Depends(deps.get_db)):
    """
    Detailed health check that verifies database connectivity.
    
    This endpoint attempts to connect to the database and returns more detailed
    health information about the system.
    """
    # Verify database connection
    db_status = "ok"
    try:
        # Simple query to verify connection is working
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status
    }
