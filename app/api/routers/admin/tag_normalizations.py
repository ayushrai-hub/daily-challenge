"""
Router configuration for tag normalization admin endpoints.
"""
from fastapi import APIRouter

from app.api.endpoints.admin.tag_normalizations import router as tag_normalizations_router

# Simple router for tag normalization endpoints
router = APIRouter(
    tags=["admin", "tags"],
    # Disable automatic redirects for trailing slashes
    # This prevents the redirect from /tag-normalizations to /tag-normalizations/ 
    # which was causing authentication headers to be lost
    redirect_slashes=False
)

# Include the tag normalizations endpoints
# Note: Stats endpoint is now defined directly in tag_normalizations.py
router.include_router(tag_normalizations_router)
