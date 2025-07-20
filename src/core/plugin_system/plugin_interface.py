"""Plugin Interface Abstract Base Class.

This module defines the contract that all plugins must implement to be compatible
with the MCP Server's plugin system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class PluginMetadata(BaseModel):
    """Metadata for a plugin that describes its capabilities."""
    
    name: str = Field(..., description="Unique name of the plugin")
    version: str = Field(..., description="Plugin version (semantic versioning)")
    description: str = Field(..., description="Brief description of plugin functionality")
    author: str = Field(..., description="Plugin author or team")
    capabilities: List[str] = Field(
        default_factory=list,
        description="List of capabilities/keywords for semantic routing"
    )
    required_params: Dict[str, str] = Field(
        default_factory=dict,
        description="Required parameters and their descriptions"
    )
    optional_params: Dict[str, str] = Field(
        default_factory=dict,
        description="Optional parameters and their descriptions"
    )
    examples: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Example usage scenarios"
    )


class PluginRequest(BaseModel):
    """Standard request format for plugin execution."""
    
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str = Field(..., description="The action to perform")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the action"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context from the router"
    )


class PluginResponse(BaseModel):
    """Standard response format from plugin execution."""
    
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(..., description="success, error, or partial")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if status is error")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the response"
    )


class Plugin(ABC):
    """Abstract base class for all MCP Server plugins."""
    
    def __init__(self) -> None:
        """Initialize the plugin."""
        self._metadata: Optional[PluginMetadata] = None
        self._initialized: bool = False
    
    @abstractmethod
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin with optional configuration.
        
        Args:
            config: Optional configuration dictionary for the plugin
            
        Raises:
            Exception: If initialization fails
        """
        pass
    
    @abstractmethod
    async def execute(self, request: PluginRequest) -> PluginResponse:
        """Execute the plugin's main functionality.
        
        Args:
            request: The plugin request containing action and parameters
            
        Returns:
            PluginResponse: The result of the plugin execution
            
        Raises:
            Exception: If execution fails
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shutdown the plugin and clean up resources.
        
        Raises:
            Exception: If shutdown fails
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get the plugin's metadata.
        
        Returns:
            PluginMetadata: The plugin's metadata
        """
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if the plugin is initialized.
        
        Returns:
            bool: True if initialized, False otherwise
        """
        return self._initialized
    
    async def validate_request(self, request: PluginRequest) -> bool:
        """Validate a request against the plugin's requirements.
        
        Args:
            request: The request to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        metadata = self.get_metadata()
        
        # Check required parameters
        for param in metadata.required_params:
            if param not in request.parameters:
                return False
        
        return True
    
    def __str__(self) -> str:
        """String representation of the plugin."""
        metadata = self.get_metadata()
        return f"{metadata.name} v{metadata.version}"
    
    def __repr__(self) -> str:
        """Detailed representation of the plugin."""
        metadata = self.get_metadata()
        return (
            f"<Plugin {metadata.name} v{metadata.version} "
            f"initialized={self._initialized}>"
        ) 