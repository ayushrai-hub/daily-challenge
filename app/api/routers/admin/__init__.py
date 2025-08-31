"""
Router configuration for admin endpoints.
"""
from fastapi import APIRouter

from app.api.routers.admin.tag_normalizations import router as tag_normalizations_router
from app.api.routers.admin.dashboard import router as dashboard_router
from app.api.routers.admin.tag_hierarchy import router as tag_hierarchy_router
from app.api.routers.admin.problems import router as problems_router
from app.api.routers.admin.users import router as users_router

# Create parent router for admin endpoints
router = APIRouter(
    tags=["admin"],
    # Disable automatic redirects for trailing slashes
    # This prevents authentication issues during redirects
    redirect_slashes=False
)

# Include tag normalization router
router.include_router(tag_normalizations_router, prefix="/tag-normalizations")

# Include dashboard router
router.include_router(dashboard_router, prefix="/dashboard")

# Include tag hierarchy router
router.include_router(tag_hierarchy_router, prefix="/tag-hierarchy")

# Include problems management router
router.include_router(problems_router)

# Include users management router
router.include_router(users_router, prefix="/users")
