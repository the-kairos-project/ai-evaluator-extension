# MCP Server Integrations

## Overview

This directory contains documentation for integrating external services and MCP servers with the main MCP Server.

## Available Documentation

### External MCP Integration

- [**External MCP Integration Pattern**](EXTERNAL_MCP_INTEGRATION.md) - Comprehensive guide for integrating external MCP servers
- [**Quick Start Guide**](QUICK_START.md) - Step-by-step tutorial for creating your first external integration
- [**LinkedIn Plugin Documentation**](LINKEDIN_PLUGIN.md) - Detailed guide for using the LinkedIn integration

## Integration Examples

### LinkedIn MCP Server

The LinkedIn integration demonstrates a complete external MCP integration:

- **Location**: `src/plugins/linkedin_external_plugin.py`
- **External Server**: [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server)
- **Features**:
  - Profile scraping
  - Company information extraction
  - Cookie-based authentication
  - Automatic process management

## Key Concepts

### 1. External MCP Protocol

External MCP servers communicate via HTTP with Server-Sent Events (SSE) for streaming responses. The protocol follows JSON-RPC 2.0 standards.

### 2. Plugin Wrapper Pattern

Each external integration requires a plugin wrapper that:
- Manages the external process lifecycle
- Handles protocol translation
- Implements error recovery
- Provides a consistent interface

### 3. Process Management

The `ExternalMCPProcess` class handles:
- Starting and stopping external servers
- Health checking
- Port management
- Automatic restart on failure

## Creating New Integrations

1. **Choose Your External Server**
   - Must support MCP protocol over HTTP/SSE
   - Should provide a streamable HTTP endpoint

2. **Create Plugin Wrapper**
   - Extend the `Plugin` base class
   - Implement initialization, execution, and shutdown
   - Handle errors gracefully

3. **Configure Environment**
   - Add necessary environment variables
   - Configure timeouts and retries
   - Set up authentication

4. **Test Thoroughly**
   - Unit test the plugin wrapper
   - Integration test with the external server
   - Test error scenarios

## Best Practices

1. **Resource Management**
   - Always clean up processes on shutdown
   - Implement proper timeout handling
   - Monitor memory usage

2. **Error Handling**
   - Provide meaningful error messages
   - Implement retry logic for transient failures
   - Log errors for debugging

3. **Security**
   - Use environment variables for secrets
   - Run external servers on localhost
   - Validate all external responses

4. **Performance**
   - Reuse HTTP connections
   - Implement connection pooling
   - Consider caching for expensive operations

## Support

For questions or issues:
1. Check the [troubleshooting guide](EXTERNAL_MCP_INTEGRATION.md#troubleshooting)
2. Review existing integrations for examples
3. Open an issue in the repository 