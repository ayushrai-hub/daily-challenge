"""
Router configuration for admin dashboard endpoints.
"""
from fastapi import APIRouter

from app.api.endpoints.admin.dashboard import router as dashboard_endpoints_router

# Create router for admin dashboard endpoints
router = APIRouter(tags=["admin", "dashboard"])

# Include dashboard endpoints
router.include_router(dashboard_endpoints_router)
