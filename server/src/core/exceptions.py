"""
Custom exceptions for the MCP Server.

This module defines a hierarchical exception structure that provides:
- Clear error categorization for different failure modes
- Detailed error context with the 'details' field
- Cause tracking for debugging nested failures
- Proper HTTP status code mapping in the API layer

Design decision: We use a base MCPException class with consistent
structure (message, details, cause) to ensure all errors can be
handled uniformly while still providing specific error types for
different failure scenarios.
"""

from typing import Optional, Dict, Any


class MCPException(Exception):
    """Base exception for all MCP-related errors.
    
    Attributes:
        message: Human-readable error message
        details: Additional context about the error
        cause: Original exception that caused this error
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
        
    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


# Plugin-related exceptions
class PluginException(MCPException):
    """Base exception for plugin-related errors."""
    pass


class PluginNotFoundError(PluginException):
    """Raised when a requested plugin is not found."""
    
    def __init__(self, plugin_name: str):
        super().__init__(
            f"Plugin '{plugin_name}' not found",
            details={"plugin_name": plugin_name}
        )


class PluginInitializationError(PluginException):
    """Raised when a plugin fails to initialize."""
    
    def __init__(self, plugin_name: str, reason: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Failed to initialize plugin '{plugin_name}': {reason}",
            details={"plugin_name": plugin_name, "reason": reason},
            cause=cause
        )


class PluginExecutionError(PluginException):
    """Raised when plugin execution fails."""
    
    def __init__(self, plugin_name: str, action: str, reason: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Plugin '{plugin_name}' failed to execute action '{action}': {reason}",
            details={"plugin_name": plugin_name, "action": action, "reason": reason},
            cause=cause
        )


class PluginValidationError(PluginException):
    """Raised when plugin request validation fails."""
    
    def __init__(self, plugin_name: str, validation_errors: Dict[str, Any]):
        super().__init__(
            f"Validation failed for plugin '{plugin_name}'",
            details={"plugin_name": plugin_name, "validation_errors": validation_errors}
        )


class PluginLoadError(PluginException):
    """Raised when a plugin fails to load."""
    
    def __init__(self, plugin_name: str, reason: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Failed to load plugin '{plugin_name}': {reason}",
            details={"plugin_name": plugin_name, "reason": reason},
            cause=cause
        )


# External MCP exceptions
class ExternalMCPException(MCPException):
    """Base exception for external MCP integration errors."""
    pass


class MCPConnectionError(ExternalMCPException):
    """Raised when connection to external MCP server fails."""
    
    def __init__(self, server_url: str, reason: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Failed to connect to MCP server at {server_url}: {reason}",
            details={"server_url": server_url, "reason": reason},
            cause=cause
        )


class MCPSessionError(ExternalMCPException):
    """Raised when MCP session management fails."""
    
    def __init__(self, operation: str, reason: str, session_id: Optional[str] = None):
        super().__init__(
            f"MCP session {operation} failed: {reason}",
            details={"operation": operation, "session_id": session_id, "reason": reason}
        )


class MCPProtocolError(ExternalMCPException):
    """Raised when MCP protocol communication fails."""
    
    def __init__(self, method: str, reason: str, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"MCP protocol error in method '{method}': {reason}",
            details={"method": method, "reason": reason, "response_data": response_data}
        )


class MCPTimeoutError(ExternalMCPException):
    """Raised when MCP request times out."""
    
    def __init__(self, operation: str, timeout: int):
        super().__init__(
            f"MCP {operation} timed out after {timeout} seconds",
            details={"operation": operation, "timeout": timeout}
        )


class ExternalProcessError(ExternalMCPException):
    """Raised when external process management fails."""
    
    def __init__(self, command: str, reason: str, exit_code: Optional[int] = None):
        super().__init__(
            f"External process '{command}' failed: {reason}",
            details={"command": command, "reason": reason, "exit_code": exit_code}
        )


# Routing exceptions
class RoutingException(MCPException):
    """Base exception for routing-related errors."""
    pass


class NoPluginsAvailableError(RoutingException):
    """Raised when no plugins are available for routing."""
    
    def __init__(self) -> None:
        super().__init__("No plugins available for routing")


class RoutingDecisionError(RoutingException):
    """Raised when routing decision fails."""
    
    def __init__(self, query: str, reason: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Failed to route query '{query}': {reason}",
            details={"query": query, "reason": reason},
            cause=cause
        )


class MultiStepExecutionError(RoutingException):
    """Raised when multi-step execution fails."""
    
    def __init__(self, step_index: int, total_steps: int, reason: str):
        super().__init__(
            f"Multi-step execution failed at step {step_index + 1}/{total_steps}: {reason}",
            details={"step_index": step_index, "total_steps": total_steps, "reason": reason}
        )


# Authentication exceptions
class AuthenticationException(MCPException):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthenticationException):
    """Raised when credentials are invalid."""
    
    def __init__(self, username: str):
        super().__init__(
            "Invalid username or password",
            details={"username": username}
        )


class InactiveUserError(AuthenticationException):
    """Raised when user account is inactive."""
    
    def __init__(self, username: str):
        super().__init__(
            f"User account '{username}' is inactive",
            details={"username": username}
        )


class InsufficientPermissionsError(AuthenticationException):
    """Raised when user lacks required permissions."""
    
    def __init__(self, required_scopes: list, user_scopes: list):
        super().__init__(
            "Insufficient permissions",
            details={"required_scopes": required_scopes, "user_scopes": user_scopes}
        )


class UserAlreadyExistsError(AuthenticationException):
    """Raised when attempting to create a user that already exists."""
    
    def __init__(self, username: str):
        super().__init__(
            f"User '{username}' already exists",
            details={"username": username}
        )


# Configuration exceptions
class ConfigurationError(MCPException):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, config_key: str, reason: str):
        super().__init__(
            f"Configuration error for '{config_key}': {reason}",
            details={"config_key": config_key, "reason": reason}
        )


# Validation exceptions
class ValidationError(MCPException):
    """Raised when input validation fails."""
    
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            details={"field": field, "value": value, "reason": reason}
        )


class ExpressionValidationError(ValidationError):
    """Raised when expression validation fails (e.g., in calculator)."""
    
    def __init__(self, expression: str, reason: str):
        super().__init__(
            "expression",
            expression,
            reason
        ) 