"""
External MCP Client for communicating with MCP servers via HTTP.

This module provides an HTTP client that can communicate with external MCP servers
running in streamable-http mode, translating between our plugin interface and MCP protocol.
"""

import asyncio
from typing import Any, Dict, List, Optional
import aiohttp
import structlog

from .external_mcp_models import MCPToolCall, MCPToolResponse
from ..protocol.sse_parser import SSEParser, SSEParseError
from ..protocol.mcp_constants import (
    MCP_PROTOCOL_VERSION,
    MCP_CLIENT_NAME,
    MCP_CLIENT_VERSION,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    HEALTHY_STATUS_CODES,
    SUCCESS_STATUS_CODES,
    MCP_BASE_ENDPOINT,
    MCP_MESSAGE_ENDPOINT,
    MCPMethod,
    MCPHeaders,
    CONTENT_TYPE_JSON,
    ACCEPT_SSE,
    ACCEPT_EVENT_STREAM,
    JSONRPC_VERSION,
    DEFAULT_REQUEST_ID,
)
from ..exceptions import (
    MCPConnectionError,
    MCPSessionError,
    MCPProtocolError,
    MCPTimeoutError,
)

logger = structlog.get_logger(__name__)


class ExternalMCPClient:
    """HTTP client for communicating with external MCP servers."""
    
    def __init__(
        self,
        server_url: str,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES
    ):
        """Initialize the external MCP client.
        
        Args:
            server_url: Base URL of the external MCP server
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        self.session_id: Optional[str] = None
        self.initialized: bool = False
        
    async def __aenter__(self) -> "ExternalMCPClient":
        """Enter async context manager and create HTTP session.
        
        Returns:
            Self for use in async with statement.
        """
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager and cleanup resources.
        
        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        if self.session:
            await self.session.close()
            
    async def initialize_session(self) -> None:
        """Initialize MCP session with the external server.
        
        This method performs the MCP handshake:
        1. Gets a session ID from the server
        2. Sends the initialize request
        3. Sends the initialized notification
        
        Raises:
            MCPSessionError: If session initialization fails.
            MCPProtocolError: If protocol communication fails.
        """
        await self._initialize_mcp_session()
    

    
    def _build_initialize_request(self) -> Dict[str, Any]:
        """Build the MCP initialize request.
        
        Returns:
            Dict[str, Any]: Initialize request data
        """
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": DEFAULT_REQUEST_ID,
            "method": MCPMethod.INITIALIZE,
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": MCP_CLIENT_NAME,
                    "version": MCP_CLIENT_VERSION
                }
            }
        }
    
    async def _send_initialize_request(self, init_request: Dict[str, Any]) -> None:
        """Send the initialize request to the MCP server.
        
        Args:
            init_request: Initialize request data
            
        Raises:
            Exception: If initialization fails
        """
        headers = {
            MCPHeaders.ACCEPT.value: "application/json, text/event-stream"
        }
        # Don't include session ID in initialize request headers
        # Don't set Content-Type manually - aiohttp will set it when using json parameter
        
        # LinkedIn MCP server uses /mcp/ endpoint with trailing slash
        endpoint = f"{self.server_url}/mcp/"
        
        # Log request details for debugging
        logger.info(
            "Sending initialize request",
            endpoint=endpoint,
            headers=headers,
            request_body=init_request
        )
        
        async with self.session.post(
            endpoint,
            json=init_request,
            headers=headers
        ) as response:
            # Log response details
            logger.info(
                "Received response",
                status=response.status,
                response_headers=dict(response.headers),
                request_headers=dict(response.request_info.headers)
            )
            
            if response.status == 200:
                # Extract session ID from response headers if present
                session_id = response.headers.get(MCPHeaders.SESSION_ID)
                if session_id:
                    self.session_id = session_id
                    logger.debug("Got session ID from initialize response", session_id=session_id)
                
                # Read and parse SSE response
                text = await response.text()
                try:
                    success, result, error_msg = SSEParser.parse_mcp_result(text)
                    if not success:
                        raise MCPProtocolError(
                            MCPMethod.INITIALIZE,
                            f"MCP initialization error: {error_msg}",
                            result
                        )
                except SSEParseError as e:
                    raise MCPProtocolError(
                        MCPMethod.INITIALIZE,
                        f"Failed to parse MCP response: {e}",
                        {"raw_data": text}
                    )
            else:
                raise MCPProtocolError(
                    MCPMethod.INITIALIZE,
                    f"Failed to initialize MCP session: {response.status}",
                    {"status": response.status}
                )
    
    async def _initialize_mcp_session(self) -> None:
        """Perform the complete MCP session initialization handshake.
        
        This internal method orchestrates the session initialization:
        1. Builds and sends the initialize request
        2. Retrieves session ID from the initialize response
        3. Sends the initialized notification to complete handshake
        
        The session is marked as initialized only after all steps succeed.
        """
        logger.info("Starting MCP session initialization")
        
        init_request = self._build_initialize_request()
        await self._send_initialize_request(init_request)
        
        await self._send_initialized_notification()
        
        self.initialized = True
        logger.info("MCP session initialized successfully", session_id=self.session_id)
    
    async def _send_initialized_notification(self) -> None:
        """Send the initialized notification to complete MCP handshake.
        
        This notification confirms to the server that the client has
        successfully processed the initialize response and is ready
        for normal operations.
        
        Raises:
            MCPProtocolError: If the notification fails to send.
        """
        notification = {
            "jsonrpc": JSONRPC_VERSION,
            "method": MCPMethod.INITIALIZED
        }
        
        headers = {
            MCPHeaders.ACCEPT.value: "application/json, text/event-stream"
        }
        
        # Include session ID if we have one
        if self.session_id:
            headers[MCPHeaders.SESSION_ID.value] = self.session_id
        
        # LinkedIn MCP server uses /mcp/ endpoint with trailing slash
        endpoint = f"{self.server_url}/mcp/"
        async with self.session.post(
            endpoint,
            json=notification,
            headers=headers
        ) as response:
            # Accept both 200 and 202 (Accepted) as success for notifications
            # MCP spec allows async processing of notifications
            if response.status not in SUCCESS_STATUS_CODES:
                raise MCPProtocolError(
                    MCPMethod.INITIALIZED,
                    f"Failed to send initialized notification: {response.status}",
                    {"status": response.status}
                )
    
    async def health_check(self) -> bool:
        """Check if the external MCP server is healthy.
        
        Returns:
            bool: True if server is responding, False otherwise
        """
        try:
            # Create a temporary session if we don't have one
            if not self.session:
                async with aiohttp.ClientSession() as temp_session:
                    async with temp_session.get(
                        f"{self.server_url}/mcp{MCP_BASE_ENDPOINT}",
                        headers={
                            MCPHeaders.ACCEPT.value: ACCEPT_EVENT_STREAM,
                            MCPHeaders.CONTENT_TYPE.value: CONTENT_TYPE_JSON
                        }
                    ) as response:
                        return response.status in HEALTHY_STATUS_CODES
            else:
                # Use existing session
                async with self.session.get(
                    f"{self.server_url}/mcp{MCP_BASE_ENDPOINT}",
                    headers={
                        MCPHeaders.ACCEPT.value: ACCEPT_EVENT_STREAM,
                        MCPHeaders.CONTENT_TYPE.value: CONTENT_TYPE_JSON
                    }
                ) as response:
                    return response.status in HEALTHY_STATUS_CODES
        except Exception as e:
            logger.warning("Health check failed", error=str(e))
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from the external MCP server.
        
        Returns:
            List[Dict[str, Any]]: List of available tools
        """
        await self.initialize_session()
        
        # MCP protocol for listing tools
        request_data = {
            "jsonrpc": JSONRPC_VERSION,
            "id": DEFAULT_REQUEST_ID,
            "method": MCPMethod.LIST_TOOLS,
            "params": {}
        }
        
        for attempt in range(self.max_retries):
            try:
                # Use the MCP endpoint for FastMCP servers - /mcp/ with trailing slash
                headers = {
                    MCPHeaders.ACCEPT.value: "application/json, text/event-stream"
                }
                if self.session_id:
                    headers[MCPHeaders.SESSION_ID.value] = self.session_id
                    
                # Don't set Content-Type manually when using json parameter
                # aiohttp will set it automatically
                async with self.session.post(
                    f"{self.server_url}/mcp/",
                    json=request_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        # Parse SSE response
                        text = await response.text()
                        try:
                            success, result, error_msg = SSEParser.parse_mcp_result(text)
                            if success and isinstance(result, dict) and "tools" in result:
                                return result["tools"]
                            elif not success:
                                logger.error("MCP error listing tools", error=error_msg)
                                return []
                            else:
                                logger.warning("Unexpected response format", result=result)
                                return []
                        except SSEParseError as e:
                            logger.warning("Failed to parse SSE response", error=str(e), text=text[:200])
                            return []
                    else:
                        logger.warning(
                            "Failed to list tools",
                            status=response.status,
                            attempt=attempt + 1
                        )
            except Exception as e:
                logger.warning(
                    "Error listing tools",
                    error=str(e),
                    attempt=attempt + 1
                )
                
            if attempt < self.max_retries - 1:
                # Exponential backoff
                retry_delay = min(2 ** (attempt - 1), 60)
                logger.info("Retrying after delay", delay_seconds=retry_delay)
                await asyncio.sleep(retry_delay)
                
        return []
    
    def _build_tool_request(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build the MCP tool call request.
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            
        Returns:
            Dict[str, Any]: Tool call request data
        """
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": DEFAULT_REQUEST_ID,
            "method": MCPMethod.CALL_TOOL,
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
    
    def _build_mcp_headers(self) -> Dict[str, str]:
        """Build standard MCP request headers.
        
        Returns:
            Dict[str, str]: Request headers
        """
        headers = {
            MCPHeaders.ACCEPT.value: "application/json, text/event-stream"
        }
        if self.session_id:
            headers[MCPHeaders.SESSION_ID.value] = self.session_id
        return headers
    
    async def _execute_tool_call(
        self,
        tool_name: str,
        request_data: Dict[str, Any],
        attempt: int
    ) -> Optional[MCPToolResponse]:
        """Execute a single tool call attempt.
        
        Args:
            tool_name: Name of the tool
            request_data: Request data
            attempt: Current attempt number
            
        Returns:
            Optional[MCPToolResponse]: Tool response if successful, None if retry needed
        """
        logger.info(
            "Calling external MCP tool",
            tool=tool_name,
            arguments=request_data["params"]["arguments"],
            attempt=attempt + 1
        )
        
        headers = self._build_mcp_headers()
        
        # LinkedIn MCP server uses /mcp/ endpoint with trailing slash
        endpoint = f"{self.server_url}/mcp/"
        async with self.session.post(
            endpoint,
            json=request_data,
            headers=headers
        ) as response:
            
            if response.status == 200:
                # Parse SSE response
                text = await response.text()
                try:
                    success, result, error_msg = SSEParser.parse_mcp_result(text)
                    
                    if success:
                        # Successful response
                        content = result.get("content", []) if isinstance(result, dict) else []
                        
                        return MCPToolResponse(
                            content=content,
                            isError=False
                        )
                    else:
                        # Error response
                        logger.error(
                            "MCP tool call error",
                            tool=tool_name,
                            error=error_msg
                        )
                        return MCPToolResponse(
                            content=[{
                                "type": "text",
                                "text": f"Error: {error_msg}"
                            }],
                            isError=True
                        )
                except SSEParseError as e:
                    logger.warning("Failed to parse tool response", error=str(e), tool=tool_name)
                    # Return None to trigger retry
                    return None
                    
            else:
                logger.warning(
                    "HTTP error calling tool",
                    tool=tool_name,
                    status=response.status,
                    attempt=attempt + 1
                )
                return None
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> MCPToolResponse:
        """Call a tool on the external MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool response with success status and result
            
        Raises:
            MCPTimeoutError: If request times out
            MCPConnectionError: If connection fails
            MCPProtocolError: If protocol error occurs
        """
        if not self.initialized:
            await self.initialize_session()
            
        request_data = self._build_tool_request(tool_name, arguments)
        
        # Try calling the tool with retries
        for attempt in range(1, self.max_retries + 1):
            logger.info(
                "Calling external MCP tool",
                tool=tool_name,
                attempt=attempt,
                max_attempts=self.max_retries
            )
            
            result = await self._execute_tool_call(tool_name, request_data, attempt)
            if result is not None:
                return result
                
            if attempt < self.max_retries:
                # Exponential backoff
                retry_delay = min(2 ** (attempt - 1), 60)
                logger.info("Retrying after delay", delay_seconds=retry_delay)
                await asyncio.sleep(retry_delay)
        
        # All attempts failed
        return MCPToolResponse(
            success=False,
            error=f"Failed to call tool '{tool_name}' after {self.max_retries} attempts",
            result=None
        )
    
    async def close(self) -> None:
        """Close the MCP client and cleanup resources.
        
        This method should be called when done with the client to:
        - Close the HTTP session
        - Release any held resources
        - Mark the session as not initialized
        
        Safe to call multiple times.
        """
        if self.session and not self.session.closed:
            await self.session.close()
        self.initialized = False
        logger.info("MCP client closed") 