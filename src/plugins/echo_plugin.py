"""Echo plugin for testing and demonstration."""

from typing import Any, Dict, Optional
import structlog

from src.core.plugin_system.plugin_interface import Plugin, PluginMetadata, PluginRequest, PluginResponse

logger = structlog.get_logger(__name__)


class EchoPlugin(Plugin):
    """A simple plugin that echoes back the input with optional transformations."""
    
    def __init__(self) -> None:
        """Initialize the Echo plugin."""
        super().__init__()
        self._metadata = PluginMetadata(
            name="echo",
            version="1.0.0",
            description="Echoes back the input with optional transformations",
            author="MCP Team",
            capabilities=["echo", "repeat", "transform", "test"],
            required_params={
                "message": "The message to echo"
            },
            optional_params={
                "uppercase": "Convert to uppercase (boolean)",
                "repeat": "Number of times to repeat (integer)",
                "prefix": "Prefix to add to the message",
                "suffix": "Suffix to add to the message"
            },
            examples=[
                {
                    "query": "Echo 'Hello World'",
                    "parameters": {"message": "Hello World"}
                },
                {
                    "query": "Repeat 'Hi' 3 times in uppercase",
                    "parameters": {"message": "Hi", "repeat": 3, "uppercase": True}
                }
            ]
        )
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the plugin.
        
        Args:
            config: Optional configuration
        """
        logger.info("Initializing Echo plugin", config=config)
        self._initialized = True
    
    async def execute(self, request: PluginRequest) -> PluginResponse:
        """Execute the echo functionality.
        
        Args:
            request: The plugin request
            
        Returns:
            PluginResponse: The echoed message
        """
        try:
            # Extract parameters
            message = request.parameters.get("message", "")
            uppercase = request.parameters.get("uppercase", False)
            repeat = request.parameters.get("repeat", 1)
            prefix = request.parameters.get("prefix", "")
            suffix = request.parameters.get("suffix", "")
            
            # Process the message
            result = message
            
            if uppercase:
                result = result.upper()
            
            if prefix:
                result = f"{prefix}{result}"
            
            if suffix:
                result = f"{result}{suffix}"
            
            # Repeat if requested
            if repeat > 1:
                result = " ".join([result] * repeat)
            
            logger.info(
                "Echo plugin executed",
                original=message,
                result=result,
                transformations={
                    "uppercase": uppercase,
                    "repeat": repeat,
                    "prefix": prefix,
                    "suffix": suffix
                }
            )
            
            return PluginResponse(
                request_id=request.request_id,
                status="success",
                data={
                    "original": message,
                    "echoed": result,
                    "transformations_applied": {
                        "uppercase": uppercase,
                        "repeat": repeat,
                        "prefix": bool(prefix),
                        "suffix": bool(suffix)
                    }
                },
                metadata={
                    "plugin": "echo",
                    "version": self._metadata.version
                }
            )
            
        except Exception as e:
            logger.error("Echo plugin execution failed", error=str(e))
            return PluginResponse(
                request_id=request.request_id,
                status="error",
                error=str(e)
            )
    
    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info("Shutting down Echo plugin")
        self._initialized = False
    
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata.
        
        Returns:
            PluginMetadata: The plugin's metadata
        """
        return self._metadata 