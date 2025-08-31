import pytest
from fastapi.exceptions import HTTPException

from app.core.exceptions import (
    BaseAppException, BadRequestException, NotFoundException,
    UnauthorizedException, ForbiddenException, ConflictException,
    InternalServerException, ServiceUnavailableException,
    DatabaseException, UnprocessableEntityException,
    http_exception_handler, ErrorDetail, ErrorResponse
)


def test_base_app_exception():
    """Test the BaseAppException."""
    # Test with default values
    exc = BaseAppException()
    assert exc.status_code == 500
    assert exc.error_code == "internal_error"
    assert exc.error_type == "Internal Error"
    assert exc.message == "An unexpected error occurred"
    assert exc.details is None
    
    # Test with custom values
    custom_msg = "Custom error message"
    custom_details = {"key": "value"}
    exc = BaseAppException(message=custom_msg, details=custom_details)
    assert exc.message == custom_msg
    assert exc.details == custom_details


def test_error_response_conversion():
    """Test converting exceptions to error responses."""
    # Create an exception
    exc = BadRequestException(message="Invalid data", details={"field": "email"})
    
    # Convert to ErrorDetail
    error_detail = exc.to_error_detail()
    assert isinstance(error_detail, ErrorDetail)
    assert error_detail.code == "bad_request"
    assert error_detail.message == "Invalid data"
    assert error_detail.details == {"field": "email"}
    
    # Convert to ErrorResponse
    path = "/api/users"
    request_id = "test-request-id"
    response = exc.to_response(path=path, request_id=request_id)
    
    assert isinstance(response, ErrorResponse)
    assert response.status_code == 400
    assert response.error == "Bad Request"
    assert response.path == path
    assert response.request_id == request_id
    
    # Check detail is correctly embedded
    assert isinstance(response.detail, ErrorDetail)
    assert response.detail.code == "bad_request"
    assert response.detail.message == "Invalid data"
    assert response.detail.details == {"field": "email"}


def test_http_exception_handler():
    """Test the http_exception_handler function."""
    # Test with string detail
    exc = http_exception_handler(404, "Resource not found")
    assert isinstance(exc, HTTPException)
    assert exc.status_code == 404
    
    response_dict = exc.detail
    assert response_dict["status_code"] == 404
    assert response_dict["error"] == "Not Found"
    assert response_dict["detail"]["code"] == "http_404"
    assert response_dict["detail"]["message"] == "Resource not found"
    
    # Test with ErrorDetail
    detail = ErrorDetail(code="custom_404", message="Custom not found")
    exc = http_exception_handler(404, detail)
    assert exc.status_code == 404
    assert exc.detail["detail"]["code"] == "custom_404"
    assert exc.detail["detail"]["message"] == "Custom not found"
    
    # Test with dict detail
    detail_dict = {"reason": "expired", "expiry_time": "2023-01-01"}
    exc = http_exception_handler(401, detail_dict)
    assert exc.status_code == 401
    assert exc.detail["error"] == "Unauthorized"
    assert exc.detail["detail"]["details"] == detail_dict


@pytest.mark.parametrize(
    "exception_class, status_code, error_code, error_type",
    [
        (BadRequestException, 400, "bad_request", "Bad Request"),
        (UnauthorizedException, 401, "unauthorized", "Unauthorized"),
        (ForbiddenException, 403, "forbidden", "Forbidden"),
        (NotFoundException, 404, "not_found", "Not Found"),
        (ConflictException, 409, "conflict", "Conflict"),
        (UnprocessableEntityException, 422, "validation_error", "Validation Error"),
        (InternalServerException, 500, "internal_server_error", "Internal Server Error"),
        (ServiceUnavailableException, 503, "service_unavailable", "Service Unavailable"),
        (DatabaseException, 500, "database_error", "Database Error"),
    ],
)
def test_specific_exceptions(exception_class, status_code, error_code, error_type):
    """Test all specific exception types."""
    exc = exception_class()
    assert exc.status_code == status_code
    assert exc.error_code == error_code
    assert exc.error_type == error_type
    
    # Test with custom message
    custom_msg = f"Custom {error_type}"
    exc = exception_class(message=custom_msg)
    assert exc.message == custom_msg
    
    # Test response conversion
    response = exc.to_response()
    assert response.status_code == status_code
    assert response.error == error_type
    assert response.detail.code == error_code
    assert response.detail.message == custom_msg


def test_validation_exception():
    """Test the UnprocessableEntityException with validation errors."""
    validation_errors = [
        {"field": "email", "message": "Invalid email format"},
        {"field": "password", "message": "Password too short"},
    ]
    
    exc = UnprocessableEntityException(
        message="Validation failed",
        errors=validation_errors,
    )
    
    assert exc.status_code == 422
    assert exc.message == "Validation failed"
    assert exc.details == {"errors": validation_errors}
    
    # Test response
    response = exc.to_response()
    assert response.status_code == 422
    assert response.error == "Validation Error"
    assert response.detail.details == {"errors": validation_errors}
