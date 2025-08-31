import os
from app.core.logging import setup_logging
setup_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routers.health import router as health_router
from app.api.routers.users import router as users_router
from app.api.routers.problems import router as problems_router
from app.api.routers.tags import router as tags_router
from app.api.routers.tag_normalization import router as tag_normalization_router
from app.api.routers.content_sources import router as content_sources_router
from app.api.routers.delivery_logs import router as delivery_logs_router
from app.api.routers.auth import router as auth_router
from app.api.routers.subscriptions import router as subscription_router
from app.api.routers.email_queue import router as email_queue_router
from app.api.routers.verification_admin import router as verification_admin_router
from app.api.routers.admin import router as admin_router
from app.api.routers.profile import router as profile_router
from app.api.routers.content_pipeline import router as content_pipeline_router
from app.api.routers.webhooks import router as webhooks_router
from app.core.config import init_settings, settings
from app.core.middleware import setup_middleware
from app.core.logging import setup_logging, get_logger
from app.core.rate_limiter import limiter

# Lifespan event handler (FastAPI best practice)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    
    This handles startup and shutdown events for the application.
    """
    # Startup
    setup_logging()  # Initialize logging system
    logger = get_logger()  # Get the configured logger
    logger.info("Starting Daily Challenge API application")
    init_settings()  # Initialize application settings
    logger.info(f"Initialized settings: {settings.model_dump_json(exclude={'SECRET_KEY', 'POSTGRES_PASSWORD'})}")
    
    yield  # Application is running
    
    # Shutdown (cleanup resources here)
    logger.info("Shutting down Daily Challenge API application")
    # Close any open database connections
    from app.db.database import engine
    if engine:
        logger.info("Closing database engine connections")
        engine.dispose()
    
    # Close any other resources that need cleanup
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Daily Challenge API",
    version="1.0.0",
    description="""
    Daily Challenge API provides programmers with daily coding problems.
    
    ## Features
    
    * User subscription management
    * Problem delivery and tracking
    * Content source integration
    * Tag-based problem categorization
    
    Visit the [GitHub repository](https://github.com/example/daily-challenge) for more information.
    """,
    contact={
        "name": "Daily Challenge Team",
        "email": "support@dailychallenge-example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_url="/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check endpoints to verify API status",
        },
        {
            "name": "authentication",
            "description": "Authentication operations including login and registration",
        },
        {
            "name": "users",
            "description": "Operations with users including registration and tag preferences",
        },
        {
            "name": "subscriptions",
            "description": "User subscription management and preferences",
        },
        {
            "name": "problems",
            "description": "Problem management and retrieval",
        },
        {
            "name": "tags",
            "description": "Tag management for problem categorization",
        },
        {
            "name": "content_sources",
            "description": "External content source management",
        },
        {
            "name": "delivery_logs",
            "description": "Tracking of problem deliveries to users",
        },
    ],
)

# Add rate limiter middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Setup middleware
setup_middleware(app)

# CORS configuration - use settings from config
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Length"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Include routers
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(problems_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(tag_normalization_router, prefix="/api")
app.include_router(content_sources_router, prefix="/api")
app.include_router(delivery_logs_router, prefix="/api")
app.include_router(subscription_router, prefix="/api")
app.include_router(email_queue_router, prefix="/api")
app.include_router(verification_admin_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(content_pipeline_router, prefix="/api/admin")
app.include_router(webhooks_router, prefix="/api")
