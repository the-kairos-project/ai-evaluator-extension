"""
MCP Protocol constants and configuration values.

Design decision: All protocol-specific constants are centralized here
to ensure consistency across the codebase and make protocol updates
easier. Using Final type hints prevents accidental modification and
provides better IDE support.
"""

from enum import Enum
from typing import Final


# Protocol Version
MCP_PROTOCOL_VERSION: Final[str] = "2024-11-05"

# Client Information
MCP_CLIENT_NAME: Final[str] = "external-mcp-client"
MCP_CLIENT_VERSION: Final[str] = "1.0.0"

# Default Timeouts (in seconds)
DEFAULT_REQUEST_TIMEOUT: Final[int] = 30
DEFAULT_HEALTH_CHECK_TIMEOUT: Final[int] = 5
DEFAULT_LINKEDIN_TIMEOUT: Final[int] = 300  # 5 minutes for LinkedIn operations
DEFAULT_STARTUP_TIMEOUT: Final[int] = 30
LINKEDIN_STARTUP_TIMEOUT: Final[int] = 60  # LinkedIn server needs more time

# Default Ports
DEFAULT_MCP_PORT: Final[int] = 8080
LINKEDIN_MCP_PORT: Final[int] = 8081  # Different port to avoid conflicts

# Default Host
DEFAULT_MCP_HOST: Final[str] = "127.0.0.1"

# Retry Configuration
DEFAULT_MAX_RETRIES: Final[int] = 3
LINKEDIN_MAX_RETRIES: Final[int] = 1  # Reduce retries for long operations

# HTTP Status Codes
HEALTHY_STATUS_CODES: Final[set] = {200, 400, 405, 406}
SUCCESS_STATUS_CODES: Final[set] = {200, 202}

# MCP Endpoints
MCP_BASE_ENDPOINT: Final[str] = "/mcp/"
MCP_MESSAGE_ENDPOINT: Final[str] = "/mcp/message"


class MCPMethod(str, Enum):
    """MCP protocol methods."""
    INITIALIZE = "initialize"
    INITIALIZED = "notifications/initialized"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"


class MCPHeaders(str, Enum):
    """Standard MCP headers."""
    SESSION_ID = "mcp-session-id"
    CONTENT_TYPE = "Content-Type"
    ACCEPT = "Accept"


# Header Values
CONTENT_TYPE_JSON: Final[str] = "application/json"
ACCEPT_SSE: Final[str] = "application/json, text/event-stream"
ACCEPT_EVENT_STREAM: Final[str] = "text/event-stream"

# JSONRPC
JSONRPC_VERSION: Final[str] = "2.0"
DEFAULT_REQUEST_ID: Final[int] = 1 