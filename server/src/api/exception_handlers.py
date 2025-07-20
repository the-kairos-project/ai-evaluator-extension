"""
Exception handlers for FastAPI application.

This module provides centralized exception handling for the API layer,
converting custom exceptions to appropriate HTTP responses.
"""

from fastapi import Request, HTTPException, status, FastAPI
from fastapi.responses import JSONResponse
import structlog

from src.core.exceptions import (
    MCPException,
    PluginNotFoundError,
    PluginInitializationError,
    PluginExecutionError,
    PluginValidationError,
    AuthenticationException,
    InvalidCredentialsError,
    InactiveUserError,
    InsufficientPermissionsError,
    UserAlreadyExistsError,
    ConfigurationError,
    ValidationError,
    ExpressionValidationError,
    MCPConnectionError,
    MCPSessionError,
    MCPProtocolError,
    MCPTimeoutError,
    ExternalProcessError,
    NoPluginsAvailableError,
    RoutingDecisionError,
    MultiStepExecutionError,
)

logger = structlog.get_logger(__name__)


async def mcp_exception_handler(request: Request, exc: MCPException) -> JSONResponse:
    """Handle MCP exceptions and convert to appropriate HTTP responses."""
    
    # Log the exception
    logger.error(
        "MCP exception occurred",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        details=getattr(exc, 'details', None),
        cause=str(exc.__cause__) if exc.__cause__ else None
    )
    
    # Map exceptions to HTTP status codes
    status_map = {
        # Plugin exceptions
        PluginNotFoundError: status.HTTP_404_NOT_FOUND,
        PluginInitializationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        PluginExecutionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        PluginValidationError: status.HTTP_400_BAD_REQUEST,
        
        # External MCP exceptions
        MCPConnectionError: status.HTTP_503_SERVICE_UNAVAILABLE,
        MCPSessionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        MCPProtocolError: status.HTTP_502_BAD_GATEWAY,
        MCPTimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
        ExternalProcessError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        
        # Routing exceptions
        NoPluginsAvailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
        RoutingDecisionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        MultiStepExecutionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        
        # Authentication exceptions
        InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
        InactiveUserError: status.HTTP_403_FORBIDDEN,
        InsufficientPermissionsError: status.HTTP_403_FORBIDDEN,
        UserAlreadyExistsError: status.HTTP_409_CONFLICT,
        
        # Validation exceptions
        ValidationError: status.HTTP_400_BAD_REQUEST,
        ExpressionValidationError: status.HTTP_400_BAD_REQUEST,
        
        # Configuration exceptions
        ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    # Get appropriate status code
    status_code = status_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Build error response
    error_detail = {
        "error": type(exc).__name__,
        "message": str(exc),
        "details": getattr(exc, 'details', None)
    }
    
    # Add cause if present
    if exc.__cause__:
        error_detail["cause"] = str(exc.__cause__)
    
    return JSONResponse(
        status_code=status_code,
        content=error_detail
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    
    logger.error(
        "Unexpected exception occurred",
        exception_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path,
        exc_info=exc
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": {"original_error": str(exc)}
            }
        }
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers with the FastAPI app."""
    
    # Register handler for all MCP exceptions
    app.add_exception_handler(MCPException, mcp_exception_handler)
    
    # Register handler for unexpected exceptions
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers registered") 