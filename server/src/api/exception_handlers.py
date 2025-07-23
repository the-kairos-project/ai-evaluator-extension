"""
Exception handlers for FastAPI application.

This module provides centralized exception handling for the API layer,
converting custom exceptions to appropriate HTTP responses.
"""

from fastapi import Request, status, FastAPI
from fastapi.responses import JSONResponse
from src.utils.logging import get_structured_logger

from src.core.exceptions import (
    MCPException,
    PluginNotFoundError,
    PluginInitializationError,
    PluginExecutionError,
    PluginValidationError,
    PluginLoadError,
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

logger = get_structured_logger(__name__)


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


async def plugin_not_found_exception_handler(request: Request, exc: PluginNotFoundError) -> JSONResponse:
    """Handle plugin not found exceptions."""
    return await mcp_exception_handler(request, exc)


async def plugin_initialization_exception_handler(request: Request, exc: PluginInitializationError) -> JSONResponse:
    """Handle plugin initialization exceptions."""
    return await mcp_exception_handler(request, exc)


async def plugin_execution_exception_handler(request: Request, exc: PluginExecutionError) -> JSONResponse:
    """Handle plugin execution exceptions."""
    return await mcp_exception_handler(request, exc)


async def plugin_validation_exception_handler(request: Request, exc: PluginValidationError) -> JSONResponse:
    """Handle plugin validation exceptions."""
    return await mcp_exception_handler(request, exc)


async def plugin_load_exception_handler(request: Request, exc: PluginLoadError) -> JSONResponse:
    """Handle plugin load exceptions."""
    return await mcp_exception_handler(request, exc)


async def value_error_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle value error exceptions."""
    return await generic_exception_handler(request, exc)


async def mcp_connection_exception_handler(request: Request, exc: MCPConnectionError) -> JSONResponse:
    """Handle MCP connection exceptions."""
    return await mcp_exception_handler(request, exc)


async def external_process_exception_handler(request: Request, exc: ExternalProcessError) -> JSONResponse:
    """Handle external process exceptions."""
    return await mcp_exception_handler(request, exc)


async def configuration_exception_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    """Handle configuration exceptions."""
    return await mcp_exception_handler(request, exc)


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation exceptions."""
    return await mcp_exception_handler(request, exc)


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers with the FastAPI app."""
    
    # Register individual exception handlers
    app.add_exception_handler(PluginNotFoundError, plugin_not_found_exception_handler)
    app.add_exception_handler(PluginInitializationError, plugin_initialization_exception_handler)
    app.add_exception_handler(PluginExecutionError, plugin_execution_exception_handler)
    app.add_exception_handler(PluginValidationError, plugin_validation_exception_handler)
    app.add_exception_handler(PluginLoadError, plugin_load_exception_handler)
    app.add_exception_handler(ValueError, value_error_exception_handler)
    app.add_exception_handler(MCPConnectionError, mcp_connection_exception_handler)
    app.add_exception_handler(ExternalProcessError, external_process_exception_handler)
    app.add_exception_handler(ConfigurationError, configuration_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # Register handler for all MCP exceptions
    app.add_exception_handler(MCPException, mcp_exception_handler)
    
    # Register handler for unexpected exceptions
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers registered") 