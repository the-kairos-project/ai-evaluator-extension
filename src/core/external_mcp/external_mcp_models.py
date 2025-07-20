"""
Data models for External MCP communication.

This module contains the data structures used for communication
with external MCP servers.
"""

from typing import Any, Dict, List
from pydantic import BaseModel


class MCPToolCall(BaseModel):
    """Represents an MCP tool call request."""
    name: str
    arguments: Dict[str, Any]


class MCPToolResponse(BaseModel):
    """Represents an MCP tool call response."""
    content: List[Dict[str, Any]]
    isError: bool = False 