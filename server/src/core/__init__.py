"""Core components of the MCP Server."""

from src.core.plugin_system.plugin_interface import Plugin, PluginMetadata, PluginRequest, PluginResponse
from src.core.plugin_system.plugin_manager import PluginManager
from src.core.protocol.mcp_protocol import MCPProtocol, MCPClient
from src.core.external_mcp.external_mcp_client import ExternalMCPClient
from src.core.external_mcp.external_mcp_process import ExternalMCPProcess

# Import exceptions
from src.core.exceptions import (
    MCPException,
    PluginException,
    PluginNotFoundError,
    PluginInitializationError,
    PluginExecutionError,
    PluginValidationError,
    ExternalMCPException,
    MCPConnectionError,
    MCPSessionError,
    MCPProtocolError,
    MCPTimeoutError,
    ExternalProcessError,
    RoutingException,
    NoPluginsAvailableError,
    RoutingDecisionError,
    MultiStepExecutionError,
    AuthenticationException,
    InvalidCredentialsError,
    InactiveUserError,
    InsufficientPermissionsError,
    UserAlreadyExistsError,
    ConfigurationError,
    ValidationError,
    ExpressionValidationError,
)

__all__ = [
    # Plugin system
    "Plugin",
    "PluginMetadata",
    "PluginRequest",
    "PluginResponse",
    "PluginManager",
    # Protocol
    "MCPProtocol",
    "MCPClient",
    "ExternalMCPClient",
    "ExternalMCPProcess",
    # Exceptions
    "MCPException",
    "PluginException",
    "PluginNotFoundError",
    "PluginInitializationError",
    "PluginExecutionError",
    "PluginValidationError",
    "ExternalMCPException",
    "MCPConnectionError",
    "MCPSessionError",
    "MCPProtocolError",
    "MCPTimeoutError",
    "ExternalProcessError",
    "RoutingException",
    "NoPluginsAvailableError",
    "RoutingDecisionError",
    "MultiStepExecutionError",
    "AuthenticationException",
    "InvalidCredentialsError",
    "InactiveUserError",
    "InsufficientPermissionsError",
    "UserAlreadyExistsError",
    "ConfigurationError",
    "ValidationError",
    "ExpressionValidationError",
] 