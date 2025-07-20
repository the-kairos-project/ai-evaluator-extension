"""Model Context Protocol (MCP) implementation for internal communication.

This module implements the MCP protocol for standardized communication
between the Semantic Router and plugins.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import structlog

logger = structlog.get_logger(__name__)


class MCPMessage(BaseModel):
    """Base MCP message structure."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: str = Field(..., description="Message type")
    version: str = Field(default="1.0", description="Protocol version")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPRequest(MCPMessage):
    """MCP request message."""
    
    type: str = Field(default="request")
    method: str = Field(..., description="Method to invoke")
    params: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[float] = Field(None, description="Request timeout in seconds")


class MCPResponse(MCPMessage):
    """MCP response message."""
    
    type: str = Field(default="response")
    request_id: str = Field(..., description="ID of the request this responds to")
    status: str = Field(..., description="success, error, or partial")
    result: Optional[Any] = Field(None, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")
    
    class Config:
        arbitrary_types_allowed = True


class MCPError(BaseModel):
    """MCP error structure."""
    
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class MCPCapability(BaseModel):
    """Describes a capability that can be invoked via MCP."""
    
    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="What this capability does")
    parameters: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Parameter definitions"
    )
    returns: Dict[str, Any] = Field(
        default_factory=dict,
        description="Return type definition"
    )
    examples: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Usage examples"
    )


class MCPRegistry(BaseModel):
    """Registry of available MCP capabilities."""
    
    capabilities: Dict[str, MCPCapability] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPProtocol:
    """Handles MCP protocol operations."""
    
    def __init__(self) -> None:
        """Initialize the MCP protocol handler."""
        self.registry = MCPRegistry()
        self._handlers: Dict[str, Any] = {}
    
    def register_capability(
        self,
        name: str,
        handler: Any,
        description: str,
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        returns: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Register a capability that can be invoked via MCP.
        
        Args:
            name: Capability name
            handler: Function or method to handle the capability
            description: Description of what the capability does
            parameters: Parameter definitions
            returns: Return type definition
            examples: Usage examples
        """
        capability = MCPCapability(
            name=name,
            description=description,
            parameters=parameters or {},
            returns=returns or {},
            examples=examples or []
        )
        
        self.registry.capabilities[name] = capability
        self._handlers[name] = handler
        
        logger.info("Registered MCP capability", name=name)
    
    def unregister_capability(self, name: str) -> None:
        """Unregister a capability.
        
        Args:
            name: Capability name to unregister
        """
        if name in self.registry.capabilities:
            del self.registry.capabilities[name]
            del self._handlers[name]
            logger.info("Unregistered MCP capability", name=name)
    
    def create_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> MCPRequest:
        """Create an MCP request.
        
        Args:
            method: Method to invoke
            params: Method parameters
            context: Additional context
            timeout: Request timeout
            
        Returns:
            MCPRequest: The created request
        """
        return MCPRequest(
            method=method,
            params=params or {},
            context=context or {},
            timeout=timeout
        )
    
    def create_response(
        self,
        request: MCPRequest,
        status: str,
        result: Optional[Any] = None,
        error: Optional[MCPError] = None
    ) -> MCPResponse:
        """Create an MCP response.
        
        Args:
            request: The request being responded to
            status: Response status
            result: Response data
            error: Error details if status is error
            
        Returns:
            MCPResponse: The created response
        """
        response = MCPResponse(
            request_id=request.id,
            status=status,
            result=result
        )
        
        if error:
            response.error = error.model_dump()
        
        return response
    
    def create_error(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> MCPError:
        """Create an MCP error.
        
        Args:
            code: Error code
            message: Error message
            details: Additional error details
            
        Returns:
            MCPError: The created error
        """
        return MCPError(
            code=code,
            message=message,
            details=details
        )
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request.
        
        Args:
            request: The request to handle
            
        Returns:
            MCPResponse: The response
        """
        logger.info(
            "Handling MCP request",
            method=request.method,
            request_id=request.id
        )
        
        # Check if method exists
        if request.method not in self._handlers:
            error = self.create_error(
                code="METHOD_NOT_FOUND",
                message=f"Method '{request.method}' not found"
            )
            return self.create_response(request, "error", error=error)
        
        # Execute handler
        try:
            handler = self._handlers[request.method]
            
            # Call handler with parameters
            if hasattr(handler, "__call__"):
                result = await handler(**request.params)
            else:
                result = handler
            
            return self.create_response(request, "success", result=result)
            
        except Exception as e:
            logger.error(
                "Error handling MCP request",
                method=request.method,
                error=str(e)
            )
            error = self.create_error(
                code="EXECUTION_ERROR",
                message=str(e),
                details={"method": request.method, "params": request.params}
            )
            return self.create_response(request, "error", error=error)
    
    def get_capabilities(self) -> Dict[str, MCPCapability]:
        """Get all registered capabilities.
        
        Returns:
            Dict[str, MCPCapability]: Registered capabilities
        """
        return self.registry.capabilities
    
    def validate_request(self, request: MCPRequest) -> Optional[MCPError]:
        """Validate an MCP request.
        
        Args:
            request: Request to validate
            
        Returns:
            Optional[MCPError]: Error if validation fails, None otherwise
        """
        # Check method exists
        if request.method not in self.registry.capabilities:
            return self.create_error(
                code="INVALID_METHOD",
                message=f"Unknown method: {request.method}"
            )
        
        # Validate parameters
        capability = self.registry.capabilities[request.method]
        required_params = {
            k: v for k, v in capability.parameters.items()
            if v.get("required", False)
        }
        
        for param_name in required_params:
            if param_name not in request.params:
                return self.create_error(
                    code="MISSING_PARAMETER",
                    message=f"Missing required parameter: {param_name}"
                )
        
        return None


class MCPClient:
    """Client for making MCP requests."""
    
    def __init__(self, protocol: MCPProtocol) -> None:
        """Initialize the MCP client.
        
        Args:
            protocol: The MCP protocol instance
        """
        self.protocol = protocol
    
    async def call(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> MCPResponse:
        """Make an MCP call.
        
        Args:
            method: Method to call
            params: Method parameters
            context: Additional context
            timeout: Request timeout
            
        Returns:
            MCPResponse: The response
        """
        request = self.protocol.create_request(
            method=method,
            params=params,
            context=context,
            timeout=timeout
        )
        
        # Validate request
        error = self.protocol.validate_request(request)
        if error:
            return self.protocol.create_response(request, "error", error=error)
        
        # Handle request
        return await self.protocol.handle_request(request) 