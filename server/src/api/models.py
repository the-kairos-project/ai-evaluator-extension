"""API request and response models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from src.core.plugin_system.plugin_interface import PluginRequest


class QueryRequest(BaseModel):
    """Request model for query processing."""
    
    query: str = Field(..., description="Natural language query")
    use_reflection: bool = Field(
        default=True,
        description="Whether to use reflection loops"
    )
    max_attempts: int = Field(
        default=3,
        description="Maximum reflection attempts",
        ge=1,
        le=5
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the query"
    )


class QueryResponse(BaseModel):
    """Response model for query processing."""
    
    query: str = Field(..., description="Original query")
    status: str = Field(..., description="Processing status")
    result: Optional[Any] = Field(None, description="Processing result")
    error: Optional[str] = Field(None, description="Error message if failed")
    explanation: Optional[str] = Field(
        None,
        description="Human-readable explanation of the processing"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PluginInfo(BaseModel):
    """Plugin information model."""
    
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    description: str = Field(..., description="Plugin description")
    capabilities: List[str] = Field(
        default_factory=list,
        description="Plugin capabilities"
    )
    loaded: bool = Field(False, description="Whether plugin is loaded")


class PluginExecuteRequest(BaseModel):
    """Request model for direct plugin execution."""
    
    action: str = Field(default="execute", description="Action to perform")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Plugin parameters"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context"
    )
    
    def to_plugin_request(self) -> PluginRequest:
        """Convert to internal PluginRequest."""
        return PluginRequest(
            action=self.action,
            parameters=self.parameters,
            context=self.context
        )


class PluginExecuteResponse(BaseModel):
    """Response model for plugin execution."""
    
    request_id: str = Field(..., description="Request ID")
    status: str = Field(..., description="Execution status")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Response metadata"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    environment: str = Field(..., description="Environment")
    plugins_loaded: int = Field(0, description="Number of loaded plugins")
    
    
class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionInfo(BaseModel):
    """Session information model."""
    
    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiration time")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Session metadata"
    )


class TaskStatus(BaseModel):
    """Task status model for async operations."""
    
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Task status")
    progress: float = Field(0.0, description="Progress percentage", ge=0, le=100)
    result: Optional[Any] = Field(None, description="Task result if completed")
    error: Optional[str] = Field(None, description="Error if failed")
    created_at: datetime = Field(..., description="Task creation time")
    updated_at: datetime = Field(..., description="Last update time")
    
    
class BatchQueryRequest(BaseModel):
    """Request model for batch query processing."""
    
    queries: List[QueryRequest] = Field(
        ...,
        description="List of queries to process",
        min_items=1,
        max_items=10
    )
    parallel: bool = Field(
        default=False,
        description="Whether to process queries in parallel"
    )
    stop_on_error: bool = Field(
        default=False,
        description="Whether to stop on first error"
    )


class BatchQueryResponse(BaseModel):
    """Response model for batch query processing."""
    
    results: List[QueryResponse] = Field(
        ...,
        description="Results for each query"
    )
    total: int = Field(..., description="Total number of queries")
    successful: int = Field(..., description="Number of successful queries")
    failed: int = Field(..., description="Number of failed queries")
    timestamp: datetime = Field(default_factory=datetime.utcnow) 