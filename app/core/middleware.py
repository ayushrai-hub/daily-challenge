import time
import uuid
import logging
from typing import Callable, Dict, Optional, Union, Any
from contextvars import ContextVar

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

# Import context variables from app.core.logging instead of importing the functions
from app.core.logging import (
    request_id_ctx_var, 
    user_id_ctx_var, 
    user_email_ctx_var, 
    user_is_admin_ctx_var
)

# Use standard logging to avoid circular import
logger = logging.getLogger(__name__)
from app.core.exceptions import (
    BaseAppException, ErrorResponse, ErrorDetail,
    DatabaseException, http_exception_handler
)
from app.core.config import get_settings  # Import get_settings instead

# Get settings
settings = get_settings()

# Context variable to store the current request path
request_path_ctx_var: ContextVar[str] = ContextVar("request_path", default="")


def get_request_id() -> str:
    """Get the request ID for the current request."""
    return request_id_ctx_var.get()


def get_request_path() -> str:
    """Get the path for the current request."""
    return request_path_ctx_var.get()


def get_user_id() -> Optional[str]:
    """Get the user ID for the current request if authenticated."""
    return user_id_ctx_var.get()


def get_user_email() -> Optional[str]:
    """Get the user email for the current request if authenticated."""
    return user_email_ctx_var.get()


def get_user_is_admin() -> bool:
    """Get whether the current user is an admin."""
    return user_is_admin_ctx_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set request context data like request ID.
    
    This middleware:
    1. Generates a unique ID for each request
    2. Sets the ID in request state
    3. Sets the ID in context variables for logging
    4. Sets the request path in context variables
    5. Adds the request ID to response headers
    """
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate unique ID for this request
        request_id = str(uuid.uuid4())
        request_path = request.url.path

        # Store in request state first (so other middleware can access it)
        request.state.request_id = request_id
        request.state.start_time = time.time()

        # Store in context variables, saving tokens for proper reset
        request_id_token = request_id_ctx_var.set(request_id)
        request_path_token = request_path_ctx_var.set(request_path)
        try:
            # Process the request
            response = await call_next(request)
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Reset context variables to prevent leakage between requests
            request_id_ctx_var.reset(request_id_token)
            request_path_ctx_var.reset(request_path_token)



class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log requests and responses.
    
    This middleware:
    1. Logs incoming requests with method, path, client IP
    2. Logs completed requests with status code and duration
    3. Includes request ID in all logs for traceability
    4. Captures user ID, email, and admin status if authenticated
    """
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract values from request
        path = request.url.path
        method = request.method
        client_host = request.client.host if request.client else "unknown"
        
        # Get request ID directly from request.state if available, then fall back to context
        # IMPORTANT: Use UUID for new requests, don't fallback to empty string
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        # Store in context variables for other modules
        request_id_ctx_var.set(request_id) 
        start_time = time.time()
        
        # Extract user information if available in request state
        user_id = None
        user_email = None
        is_admin = False
        
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            user_id = str(user.id) if hasattr(user, "id") else None
            user_email = user.email if hasattr(user, "email") else None
            is_admin = user.is_admin if hasattr(user, "is_admin") else False
            
            # Set user context variables
            user_id_ctx_var.set(user_id)
            user_email_ctx_var.set(user_email)
            user_is_admin_ctx_var.set(is_admin)
            
        # Prepare log extras
        log_extras = {
            "request_id": request_id,
            "user_id": user_id,
            "user_email": user_email,
            "is_admin": is_admin
        }
        
        # User info for log message
        user_info = ""
        if user_id:
            user_info = f" [User: {user_email} ({user_id}){' (ADMIN)' if is_admin else ''}]"
        
        # Log the incoming request with all available context
        logger.info(
            f"Request started: {method} {path} from {client_host}{user_info}",
            extra=log_extras
        )
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Calculate request duration
            process_time = time.time() - start_time
            
            # Log the completed request with status and duration
            status_code = response.status_code
            logger.info(
                f"Request completed: {method} {path} - {status_code} in {process_time:.3f}s{user_info}",
                extra=log_extras
            )
            
            return response
        except Exception as e:
            # Log the exception (it will be handled by the error handlers)
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {method} {path} in {process_time:.3f}s - {str(e)}",
                extra={"request_id": request_id}
            )
            raise


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle and format all application errors.
    
    This middleware catches and processes:
    1. Custom application exceptions
    2. SQLAlchemy database exceptions
    3. Unhandled exceptions
    
    It converts all exceptions to our standardized error response format.
    """
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)
        
        except BaseAppException as exc:
            # Already formatted application exceptions
            request_id = get_request_id()
            path = get_request_path()
            
            # Log with request_id
            logger.error(
                f"Application error: {exc.error_type} - {exc.message}",
                extra={"request_id": request_id}
            )
            
            # Convert to standard response
            error_response = exc.to_response(
                path=path,
                request_id=request_id,
            )
            
            return JSONResponse(
                status_code=exc.status_code,
                content=error_response.model_dump(),
            )
            
        except SQLAlchemyError as exc:
            # Database errors
            request_id = get_request_id()
            path = get_request_path()
            
            # Log with detailed error for debugging
            logger.error(
                f"Database error: {str(exc.__class__.__name__)} - {str(exc)}",
                extra={"request_id": request_id}
            )
            
            # Create database exception and convert to response
            # Hide actual DB error from users for security
            db_error = DatabaseException(
                message="A database error occurred",
                details={"error_type": exc.__class__.__name__} if request.app.debug else None,
            )
            
            error_response = db_error.to_response(
                path=path,
                request_id=request_id,
            )
            
            return JSONResponse(
                status_code=db_error.status_code,
                content=error_response.model_dump(),
            )
            
        except Exception as exc:
            # Unhandled exceptions
            request_id = get_request_id()
            path = get_request_path()
            
            # Log the unhandled exception
            logger.exception(
                f"Unhandled exception: {str(exc.__class__.__name__)} - {str(exc)}",
                extra={"request_id": request_id}
            )
            
            # In production, don't expose internal error details
            # In debug mode, include more information
            if request.app.debug:
                error_detail = ErrorDetail(
                    code="internal_server_error",
                    message=str(exc),
                    details={"error_type": exc.__class__.__name__},
                )
            else:
                error_detail = ErrorDetail(
                    code="internal_server_error",
                    message="An unexpected error occurred",
                )
            
            error_response = ErrorResponse(
                status_code=500,
                error="Internal Server Error",
                detail=error_detail,
                path=path,
                request_id=request_id,
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response.model_dump(),
            )


# Exception handlers for FastAPI
def setup_exception_handlers(app: FastAPI) -> None:
    """
    Set up exception handlers for FastAPI.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler_func(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle Starlette HTTP exceptions."""
        request_id = get_request_id()
        path = request.url.path
        
        logger.warning(
            f"HTTP error: {exc.status_code} - {exc.detail}"
        )
        
        error_response = ErrorResponse(
            status_code=exc.status_code,
            error=f"HTTP {exc.status_code}",
            detail=ErrorDetail(
                code=f"http_{exc.status_code}",
                message=str(exc.detail),
            ),
            path=path,
            request_id=request_id,
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(),
            headers=exc.headers,
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors."""
        request_id = get_request_id()
        path = request.url.path
        
        # Extract validation errors
        error_details = []
        for error in exc.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            error_details.append({
                "loc": loc,
                "msg": error["msg"],
                "type": error["type"],
            })
        
        logger.warning(
            f"Validation error: {path} - {error_details}"
        )
        
        error_response = ErrorResponse(
            status_code=422,
            error="Validation Error",
            detail=ErrorDetail(
                code="validation_error",
                message="Request validation error",
                details={"errors": error_details},
            ),
            path=path,
            request_id=request_id,
        )
        
        return JSONResponse(
            status_code=422,
            content=error_response.model_dump(),
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler_func(request: Request, exc: Exception) -> JSONResponse:
        """Handle all other exceptions that are not caught by more specific handlers."""
        request_id = get_request_id()
        path = request.url.path
        
        # Log the full exception with traceback for server-side debugging
        logger.exception(f"Unhandled exception: {exc}")
        
        # In testing/debug mode, return more detailed error information
        if settings.TESTING or settings.DEBUG:
            import traceback
            error_detail = ErrorDetail(
                code="internal_server_error",
                message=str(exc),
                details={
                    "error_type": exc.__class__.__name__,
                    "traceback": traceback.format_exc()
                },
            )
        else:
            error_detail = ErrorDetail(
                code="internal_server_error",
                message="An unexpected error occurred",
            )
        
        error_response = ErrorResponse(
            status_code=500,
            error="Internal Server Error",
            detail=error_detail,
            path=path,
            request_id=request_id,
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(),
        )


def setup_middleware(app: FastAPI) -> None:
    """
    Set up all middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Order is important: RequestContext first, then logging, then error handling
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    
    # Set up exception handlers
    setup_exception_handlers(app)
