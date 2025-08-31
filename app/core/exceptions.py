from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """
    Model for a detailed error message.
    
    Provides structured error information including a code,
    human-readable message, and optional additional details.
    """
    code: str = Field(..., description="Unique error code for the error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")


class ErrorResponse(BaseModel):
    """
    Standardized error response model.
    
    This is the format that all API error responses will follow,
    with consistent structure for error handling by clients.
    """
    status_code: int = Field(..., description="HTTP status code")
    error: str = Field(..., description="Error type or category")
    detail: Union[str, ErrorDetail, List[ErrorDetail]] = Field(
        ..., description="Error details - string or structured error information"
    )
    path: Optional[str] = Field(None, description="API path where the error occurred")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")


class BaseAppException(Exception):
    """
    Base exception for all application exceptions.
    
    All custom exceptions should inherit from this class to ensure
    they can be properly handled by the global exception handlers.
    """
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"
    error_type: str = "Internal Error"
    
    def __init__(
        self,
        message: str = "An unexpected error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def to_error_detail(self) -> ErrorDetail:
        """Convert exception to ErrorDetail."""
        return ErrorDetail(
            code=self.error_code,
            message=self.message,
            details=self.details,
        )
    
    def to_response(self, path: Optional[str] = None, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert exception to standardized ErrorResponse."""
        return ErrorResponse(
            status_code=self.status_code,
            error=self.error_type,
            detail=self.to_error_detail(),
            path=path,
            request_id=request_id,
        )


# 4xx Client Error Exceptions
class BadRequestException(BaseAppException):
    """Exception for invalid request format or parameters."""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "bad_request"
    error_type = "Bad Request"


class UnauthorizedException(BaseAppException):
    """Exception for authentication failures."""
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"
    error_type = "Unauthorized"


class ForbiddenException(BaseAppException):
    """Exception for permission/authorization failures."""
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"
    error_type = "Forbidden"


class NotFoundException(BaseAppException):
    """Exception for resources that don't exist."""
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"
    error_type = "Not Found"


class ConflictException(BaseAppException):
    """Exception for resource conflicts (e.g. already exists)."""
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"
    error_type = "Conflict"


class UnprocessableEntityException(BaseAppException):
    """Exception for validation errors."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_error"
    error_type = "Validation Error"
    
    def __init__(
        self,
        message: str = "Validation error",
        errors: Optional[List[Dict[str, Any]]] = None,
    ):
        details = {"errors": errors} if errors else None
        super().__init__(message=message, details=details)


# 5xx Server Error Exceptions
class InternalServerException(BaseAppException):
    """Exception for unexpected server errors."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "internal_server_error"
    error_type = "Internal Server Error"


class ServiceUnavailableException(BaseAppException):
    """Exception for when a service is temporarily unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "service_unavailable"
    error_type = "Service Unavailable"


class DatabaseException(BaseAppException):
    """Exception for database errors."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "database_error"
    error_type = "Database Error"


# Convert FastAPI HTTPException to our format
def http_exception_handler(status_code: int, detail: Any, headers: Optional[Dict[str, Any]] = None) -> HTTPException:
    """
    Create a FastAPI HTTPException with standardized format.
    
    This helper ensures all manually raised HTTPExceptions
    follow our standardized error format.
    
    Args:
        status_code: HTTP status code
        detail: Error details
        headers: Optional HTTP headers
    
    Returns:
        FastAPI HTTPException
    """
    if isinstance(detail, str):
        error_detail = ErrorDetail(
            code=f"http_{status_code}",
            message=detail,
        )
    elif isinstance(detail, ErrorDetail):
        error_detail = detail
    else:
        error_detail = ErrorDetail(
            code=f"http_{status_code}",
            message=str(detail),
            details=detail if isinstance(detail, dict) else None,
        )
    
    response = ErrorResponse(
        status_code=status_code,
        error=status_code_to_error_type(status_code),
        detail=error_detail,
    )
    
    return HTTPException(
        status_code=status_code,
        detail=response.model_dump(),
        headers=headers,
    )


def status_code_to_error_type(status_code: int) -> str:
    """Map HTTP status code to error type string."""
    error_map = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        422: "Validation Error",
        500: "Internal Server Error",
        503: "Service Unavailable",
    }
    return error_map.get(status_code, "Error")
