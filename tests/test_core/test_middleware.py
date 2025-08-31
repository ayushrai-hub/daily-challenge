import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.core.middleware import (
    RequestContextMiddleware, LoggingMiddleware, 
    ErrorHandlerMiddleware, setup_middleware,
    get_request_id, request_id_ctx_var, get_request_path,
    request_path_ctx_var
)
from app.core.exceptions import BadRequestException


@pytest.fixture
def app():
    """Create a test FastAPI app."""
    return FastAPI()


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/test/path"
    request.method = "GET"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = MagicMock()
    response.headers = {}
    response.status_code = 200
    return response


class TestRequestContextMiddleware:
    """Tests for the RequestContextMiddleware."""
    
    @pytest.mark.asyncio
    async def test_request_context_middleware(self, mock_request, mock_response):
        """Test that request context middleware sets request ID."""
        # Setup
        middleware = RequestContextMiddleware(app=None)
        mock_call_next = AsyncMock(return_value=mock_response)
        
        # Execute
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Verify
        # Request ID was set in request state
        assert hasattr(mock_request.state, "request_id")
        assert mock_request.state.request_id is not None
        # Request ID is a valid UUID
        uuid.UUID(mock_request.state.request_id)
        # Request ID was set in response header
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] == mock_request.state.request_id
        # Start time was set
        assert hasattr(mock_request.state, "start_time")
        
    @pytest.mark.asyncio
    async def test_request_context_variables(self, mock_request, mock_response):
        """Test that context variables are properly set and can be retrieved."""
        # Setup
        middleware = RequestContextMiddleware(app=None)
        mock_call_next = AsyncMock(return_value=mock_response)
        
        # Execute
        await middleware.dispatch(mock_request, mock_call_next)
        
        # Get values from context variables
        request_id = get_request_id()
        request_path = get_request_path()
        
        # Verify
        assert request_id == mock_request.state.request_id
        assert request_path == "/test/path"


class TestLoggingMiddleware:
    """Tests for the LoggingMiddleware."""
    
    @pytest.mark.asyncio
    @patch("app.core.middleware.logger")
    async def test_logging_middleware_success(self, mock_logger, mock_request, mock_response):
        """Test that logging middleware logs request and response."""
        # Setup
        middleware = LoggingMiddleware(app=None)
        mock_call_next = AsyncMock(return_value=mock_response)
        
        # Set request ID in context var
        test_request_id = str(uuid.uuid4())
        request_id_ctx_var.set(test_request_id)
        
        # Execute
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Verify
        # Request log
        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_any_call(
            f"Request started: GET /test/path from 127.0.0.1",
            extra={"request_id": test_request_id}
        )
        # Response log
        # Extract duration from the second call args
        call_args_list = mock_logger.info.call_args_list
        response_log_args = next(args for args, kwargs in call_args_list if "Request completed" in args[0])
        mock_logger.info.assert_any_call(
            f"Request completed: GET /test/path - 200 in {response_log_args[0].split('in ')[1]}",
            extra={"request_id": test_request_id}
        )
    
    @pytest.mark.asyncio
    @patch("app.core.middleware.logger")
    async def test_logging_middleware_error(self, mock_logger, mock_request):
        """Test that logging middleware logs errors."""
        # Setup
        middleware = LoggingMiddleware(app=None)
        test_exception = ValueError("Test error")
        mock_call_next = AsyncMock(side_effect=test_exception)
        
        # Set request ID in context var
        test_request_id = str(uuid.uuid4())
        request_id_ctx_var.set(test_request_id)
        
        # Execute
        with pytest.raises(ValueError):
            await middleware.dispatch(mock_request, mock_call_next)
        
        # Verify
        # Request log
        assert mock_logger.info.call_count == 1
        mock_logger.info.assert_called_once_with(
            f"Request started: GET /test/path from 127.0.0.1",
            extra={"request_id": test_request_id}
        )
        
        # Error log
        assert mock_logger.error.call_count == 1
        error_call_args = mock_logger.error.call_args
        assert "Request failed" in error_call_args[0][0]
        assert "Test error" in error_call_args[0][0]
        assert error_call_args[1] == {"extra": {"request_id": test_request_id}}


class TestErrorHandlerMiddleware:
    """Tests for the ErrorHandlerMiddleware."""
    
    @pytest.mark.asyncio
    async def test_error_handler_app_exception(self, mock_request, mock_response):
        """Test handling of application exceptions."""
        # Setup
        middleware = ErrorHandlerMiddleware(app=None)
        test_exception = BadRequestException(message="Invalid input")
        mock_call_next = AsyncMock(side_effect=test_exception)
        
        # Set request ID in context var
        test_request_id = str(uuid.uuid4())
        request_id_ctx_var.set(test_request_id)
        
        # Execute
        with patch("app.core.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Verify
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        content = response.body.decode("utf-8")
        assert "Bad Request" in content
        assert "Invalid input" in content
        
        # Verify logger was called correctly
        assert mock_logger.error.call_count == 1
        error_call_args = mock_logger.error.call_args
        assert "Application error" in error_call_args[0][0]
        assert "Invalid input" in error_call_args[0][0]
        assert error_call_args[1] == {"extra": {"request_id": test_request_id}}
    
    @pytest.mark.asyncio
    async def test_error_handler_database_exception(self, mock_request, mock_response):
        """Test handling of database exceptions."""
        # Setup
        middleware = ErrorHandlerMiddleware(app=None)
        test_exception = SQLAlchemyError("Database error")
        mock_call_next = AsyncMock(side_effect=test_exception)
        mock_request.app.debug = False
        
        # Set request ID in context var
        test_request_id = str(uuid.uuid4())
        request_id_ctx_var.set(test_request_id)
        
        # Execute
        with patch("app.core.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Verify
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        content = response.body.decode("utf-8")
        assert "Database Error" in content
        assert "A database error occurred" in content
        assert test_request_id in content
        
        # In non-debug mode, details should be hidden
        assert "SQLAlchemyError" not in content
        
        # Verify logger was called correctly
        assert mock_logger.error.call_count == 1
        error_call_args = mock_logger.error.call_args
        assert "Database error" in error_call_args[0][0]
        assert "SQLAlchemyError" in error_call_args[0][0]
        assert error_call_args[1] == {"extra": {"request_id": test_request_id}}
    
    @pytest.mark.asyncio
    async def test_error_handler_unhandled_exception(self, mock_request, mock_response):
        """Test handling of unhandled exceptions."""
        # Setup
        middleware = ErrorHandlerMiddleware(app=None)
        test_exception = ValueError("Test unexpected error")
        mock_call_next = AsyncMock(side_effect=test_exception)
        
        # Debug mode
        mock_request.app.debug = True
        
        # Set request ID and path in context vars
        test_request_id = str(uuid.uuid4())
        request_id_ctx_var.set(test_request_id)
        
        # Execute
        with patch("app.core.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Verify
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        content = response.body.decode("utf-8")
        assert "Internal Server Error" in content
        
        # In debug mode, details should be included
        assert "Test unexpected error" in content
        assert "ValueError" in content
        
        # Verify logger was called correctly
        assert mock_logger.exception.call_count == 1
        exception_call_args = mock_logger.exception.call_args
        assert "Unhandled exception" in exception_call_args[0][0]
        assert "Test unexpected error" in exception_call_args[0][0]
        assert exception_call_args[1] == {"extra": {"request_id": test_request_id}}
        
    @pytest.mark.asyncio
    async def test_error_handler_unhandled_exception_production(self, mock_request, mock_response):
        """Test handling of unhandled exceptions in production mode (non-debug)."""
        # Setup
        middleware = ErrorHandlerMiddleware(app=None)
        test_exception = ValueError("Test unexpected error")
        mock_call_next = AsyncMock(side_effect=test_exception)
        
        # Production mode (no debug)
        mock_request.app.debug = False
        
        # Set request ID and path in context vars
        test_request_id = str(uuid.uuid4())
        request_id_ctx_var.set(test_request_id)
        
        # Execute
        with patch("app.core.middleware.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Verify
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        content = response.body.decode("utf-8")
        assert "Internal Server Error" in content
        
        # In production mode, detailed error should be hidden
        assert "Test unexpected error" not in content
        assert "An unexpected error occurred" in content
        assert "ValueError" not in content


def test_setup_middleware(app):
    """Test that middleware setup registers all middleware."""
    # Initial state
    initial_middleware_count = len(app.user_middleware)
    
    # Execute
    setup_middleware(app)
    
    # Verify
    # Check that middleware were added
    assert len(app.user_middleware) > initial_middleware_count
    
    # Check that our middleware are there
    middleware_classes = [m.cls for m in app.user_middleware]
    assert RequestContextMiddleware in middleware_classes
    assert LoggingMiddleware in middleware_classes
    assert ErrorHandlerMiddleware in middleware_classes


# Testing the exception handler registration
from fastapi.testclient import TestClient
from pydantic import BaseModel


@pytest.mark.parametrize(
    "exception,expected_status,expected_error_type", [
        (ValueError("Test error"), 500, "Internal Server Error"),
        (BadRequestException(message="Invalid input"), 400, "Bad Request"),
        (SQLAlchemyError("DB error"), 500, "Database Error"),
    ]
)
def test_exception_handlers(app, exception, expected_status, expected_error_type):
    """Test that exception handlers properly format different types of errors."""
    # Setup a test route that raises an exception
    @app.get("/test-exception")
    def test_route():
        raise exception
    
    # Set up middleware and exception handlers
    setup_middleware(app)
    
    # Create a test client
    client = TestClient(app)
    
    # Execute request
    response = client.get("/test-exception")
    
    # Verify
    assert response.status_code == expected_status
    response_json = response.json()
    assert response_json["error"] == expected_error_type
    assert "request_id" in response_json


@pytest.mark.parametrize(
    "payload,expected_status,expected_msg", [
        # Missing required field
        ({}, 422, "Validation Error"),
        # Invalid type
        ({"value": "not-a-number"}, 422, "Validation Error"),
    ]
)
def test_validation_error_handler(app, payload, expected_status, expected_msg):
    """Test that validation errors are properly handled and formatted."""
    # Define a model with validation
    class TestModel(BaseModel):
        value: int
    
    # Setup a test route with validation
    @app.post("/test-validation")
    def test_route(data: TestModel):
        return {"result": data.value * 2}
    
    # Set up middleware and exception handlers
    setup_middleware(app)
    
    # Create a test client
    client = TestClient(app)
    
    # Execute request with invalid data
    response = client.post("/test-validation", json=payload)
    
    # Verify
    assert response.status_code == expected_status
    response_json = response.json()
    assert response_json["error"] == expected_msg
    assert "detail" in response_json
