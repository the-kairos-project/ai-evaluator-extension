# External MCP Integration Pattern

## Overview

The External MCP Integration pattern allows the MCP Server to communicate with external MCP servers running in streamable HTTP mode. This pattern enables integration with third-party MCP servers without requiring direct code integration.

## Architecture

### Components

1. **ExternalMCPClient** (`src/core/external_mcp/external_mcp_client.py`)
   - HTTP/SSE client for MCP protocol communication
   - Handles session management and tool execution
   - Implements retry logic and error handling

2. **ExternalMCPProcess** (`src/core/external_mcp/external_mcp_process.py`)
   - Process lifecycle management for external servers
   - Health checking and automatic restart
   - Port management and cleanup

3. **External Plugin Wrapper** (e.g., `src/plugins/linkedin_external_plugin.py`)
   - Implements standard Plugin interface
   - Manages ExternalMCPClient and ExternalMCPProcess
   - Translates between plugin requests and MCP protocol

### Data Flow

```
User Request → API → Plugin Manager → External Plugin Wrapper
                                              ↓
                                    ExternalMCPProcess (starts server)
                                              ↓
                                    ExternalMCPClient (HTTP/SSE)
                                              ↓
                                    External MCP Server
```

## Implementation Guide

### 1. Create an External Plugin Wrapper

```python
from src.core.plugin_system.plugin_interface import Plugin, PluginRequest, PluginResponse
from src.core.external_mcp.external_mcp_client import ExternalMCPClient
from src.core.external_mcp.external_mcp_process import ExternalMCPProcess

class MyExternalPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.process_manager = None
        self.mcp_client = None
        
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        # Start external server
        self.process_manager = ExternalMCPProcess(
            command=["node", "path/to/server.js"],
            port=8080
        )
        await self.process_manager.start()
        
        # Initialize MCP client
        self.mcp_client = ExternalMCPClient(f"http://localhost:8080")
        await self.mcp_client.initialize_session()
```

### 2. MCP Protocol Communication

The external server must support the MCP protocol over HTTP/SSE:

#### Required Endpoints

- `GET /` - Health check endpoint
- `POST /sse` - SSE endpoint for MCP messages

#### Message Format

```json
{
    "jsonrpc": "2.0",
    "method": "initialize|list_tools|call_tool",
    "params": {...},
    "id": "unique-id"
}
```

#### SSE Response Format

```
event: message
data: {"jsonrpc":"2.0","result":{...},"id":"unique-id"}
```

### 3. Session Management

Sessions are managed via HTTP headers:

```python
headers = {
    "x-session-id": "session-uuid",
    "Content-Type": "application/json",
    "Accept": "text/event-stream"
}
```

## Configuration

### Environment Variables

```bash
# External server configuration
EXTERNAL_MCP_TIMEOUT=300  # Request timeout in seconds
EXTERNAL_MCP_MAX_RETRIES=3  # Maximum retry attempts
```

### Plugin Configuration

```python
config = {
    "server_path": "/path/to/external/server",
    "port": 8080,
    "startup_timeout": 30,
    "environment": {
        "API_KEY": "your-api-key"
    }
}
```

## Error Handling

### Retry Logic

The ExternalMCPClient implements exponential backoff:

```python
retry_delay = min(2 ** (attempt - 1), 60)  # Max 60 seconds
```

### Error Types

1. **Connection Errors** - Server not reachable
2. **Protocol Errors** - Invalid MCP messages
3. **Timeout Errors** - Request exceeds timeout
4. **Session Errors** - Invalid or expired session

## Best Practices

### 1. Process Management

- Always implement proper cleanup in `shutdown()`
- Use health checks to verify server readiness
- Handle process crashes gracefully

### 2. Resource Management

```python
async def shutdown(self) -> None:
    if self.mcp_client:
        await self.mcp_client.close()
    if self.process_manager:
        await self.process_manager.stop()
```

### 3. Error Propagation

- Wrap external errors in PluginResponse
- Provide meaningful error messages
- Log errors for debugging

### 4. Performance Considerations

- Reuse HTTP sessions when possible
- Implement connection pooling for high throughput
- Monitor memory usage of external processes

## Testing

### Unit Testing

```python
@pytest.mark.asyncio
async def test_external_mcp_client():
    client = ExternalMCPClient("http://localhost:8080")
    
    # Mock HTTP responses
    with aioresponses() as m:
        m.get("http://localhost:8080/", status=200)
        assert await client.health_check()
```

### Integration Testing

1. Start external server in test fixture
2. Verify end-to-end communication
3. Test error scenarios
4. Validate cleanup

## Example: LinkedIn Integration

See `src/plugins/linkedin_external_plugin.py` for a complete implementation that:

- Manages the LinkedIn MCP server process
- Handles cookie-based authentication
- Implements profile and company scraping
- Provides comprehensive error handling

## Troubleshooting

### Common Issues

1. **Server Won't Start**
   - Check port availability
   - Verify command path
   - Review server logs

2. **Session Errors**
   - Ensure session initialization
   - Check header propagation
   - Verify server session handling

3. **Timeout Issues**
   - Increase timeout values
   - Check server performance
   - Implement streaming for large responses

### Debug Logging

Enable debug logging:

```python
import structlog
logger = structlog.get_logger(__name__)
logger.debug("MCP request", method=method, params=params)
```

## Security Considerations

1. **Authentication** - Pass credentials via environment variables
2. **Network Security** - Use localhost for external servers
3. **Input Validation** - Validate all external responses
4. **Resource Limits** - Implement timeouts and memory limits 