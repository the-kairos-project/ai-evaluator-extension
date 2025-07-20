# Quick Start: External MCP Integration

## Prerequisites

- Python 3.10+
- External MCP server executable
- Basic understanding of async Python

## Step-by-Step Guide

### 1. Create Your Plugin

Create a new file `src/plugins/my_external_plugin.py`:

```python
from typing import Any, Dict, Optional
import structlog

from src.core.plugin_system.plugin_interface import Plugin, PluginRequest, PluginResponse, PluginMetadata
from src.core.external_mcp.external_mcp_client import ExternalMCPClient
from src.core.external_mcp.external_mcp_process import ExternalMCPProcess

logger = structlog.get_logger(__name__)

class MyExternalPlugin(Plugin):
    """Plugin wrapper for external MCP server."""
    
    def __init__(self):
        super().__init__()
        self.process_manager: Optional[ExternalMCPProcess] = None
        self.mcp_client: Optional[ExternalMCPClient] = None
        
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the external MCP server and client."""
        config = config or {}
        
        # Start external server
        self.process_manager = ExternalMCPProcess(
            command=["node", "path/to/your/server.js"],
            port=8080,
            startup_timeout=30
        )
        await self.process_manager.start()
        
        # Initialize MCP client
        self.mcp_client = ExternalMCPClient("http://localhost:8080")
        await self.mcp_client.initialize_session()
        
        logger.info("External plugin initialized")
        
    async def execute(self, request: PluginRequest) -> PluginResponse:
        """Execute plugin request via external MCP server."""
        if not self.mcp_client:
            return PluginResponse(
                success=False,
                error="Plugin not initialized"
            )
            
        try:
            # Map plugin action to MCP tool
            tool_name = request.action
            arguments = request.parameters
            
            # Call external tool
            result = await self.mcp_client.call_tool(tool_name, arguments)
            
            return PluginResponse(
                success=True,
                data=result.result
            )
            
        except Exception as e:
            logger.error("External plugin error", error=str(e))
            return PluginResponse(
                success=False,
                error=str(e)
            )
            
    async def shutdown(self) -> None:
        """Clean up resources."""
        if self.mcp_client:
            await self.mcp_client.close()
        if self.process_manager:
            await self.process_manager.stop()
            
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="my_external",
            version="1.0.0",
            description="My external MCP integration",
            author="Your Name",
            capabilities=["tool1", "tool2"]
        )
```

### 2. Register Your Plugin

Add to `src/plugins/__init__.py`:

```python
from .my_external_plugin import MyExternalPlugin

__all__ = [..., "MyExternalPlugin"]
```

### 3. Configure Environment

Add to `.env`:

```bash
# External plugin configuration
MY_EXTERNAL_SERVER_PATH=/path/to/server
MY_EXTERNAL_API_KEY=your-api-key
```

### 4. Test Your Integration

```python
# tests/test_my_external_plugin.py
import pytest
from src.plugins.my_external_plugin import MyExternalPlugin

@pytest.mark.asyncio
async def test_plugin_initialization():
    plugin = MyExternalPlugin()
    await plugin.initialize()
    
    assert plugin.mcp_client is not None
    assert await plugin.mcp_client.health_check()
    
    await plugin.shutdown()

@pytest.mark.asyncio
async def test_plugin_execution():
    plugin = MyExternalPlugin()
    await plugin.initialize()
    
    request = PluginRequest(
        action="tool1",
        parameters={"param": "value"}
    )
    
    response = await plugin.execute(request)
    assert response.success
    
    await plugin.shutdown()
```

### 5. Run Your Plugin

```bash
# Start the MCP server
python -m src.api.main

# Test via API
curl -X POST http://localhost:8000/api/v1/plugins/my_external/execute \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "tool1",
    "parameters": {"param": "value"}
  }'
```

## Common Patterns

### Environment Variable Configuration

```python
import os

class MyExternalPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.server_path = os.getenv("MY_EXTERNAL_SERVER_PATH")
        self.api_key = os.getenv("MY_EXTERNAL_API_KEY")
```

### Dynamic Tool Discovery

```python
async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
    # ... initialize client ...
    
    # Discover available tools
    tools = await self.mcp_client.list_tools()
    self.available_tools = {tool["name"]: tool for tool in tools}
```

### Error Recovery

```python
async def execute(self, request: PluginRequest) -> PluginResponse:
    try:
        # Check if server is healthy
        if not await self.mcp_client.health_check():
            # Try to restart
            await self.process_manager.restart()
            await self.mcp_client.initialize_session()
            
        # Execute request
        result = await self.mcp_client.call_tool(
            request.action,
            request.parameters
        )
        
        return PluginResponse(success=True, data=result.result)
        
    except Exception as e:
        logger.error("Execution failed", error=str(e))
        return PluginResponse(success=False, error=str(e))
```

## Next Steps

1. Review the [full documentation](EXTERNAL_MCP_INTEGRATION.md)
2. Check the [LinkedIn example](../../src/plugins/linkedin_external_plugin.py)
3. Implement proper error handling
4. Add comprehensive logging
5. Write integration tests 