# Frontend-Server Integration Plan

## Overview

This document outlines the plan for integrating the Kairos frontend application with the MCP server. The integration will enable two modes of operation:

1. **Direct Mode** (current behavior): Frontend calls OpenAI/Anthropic APIs directly
2. **Server Mode** (new): Frontend routes API calls through the MCP server

Additionally, the integration will enable access to the LinkedIn plugin functionality provided by the server.

## Development Environment

### Local Setup

For initial development and testing, we'll run both components locally:

1. **Frontend (Airtable Extension)**:
   - Run in development mode with `bun run start:applications`
   - This starts the Airtable extension locally

2. **Server (MCP Server)**:
   - Run with Docker Compose: `docker-compose up -d`
   - This starts the MCP server and LinkedIn plugin server

3. **Testing Flow**:
   - Configure frontend settings to point to local server (`http://localhost:8000`)
   - Test each feature incrementally after implementation
   - Verify both direct and server-routed modes

### Production Deployment

Once tested locally, the components will be deployed separately:
- Frontend as an Airtable extension
- Server on fly.io or similar hosting platform

## Implementation Plan

### Frontend Changes

#### Settings Dialog Updates ✅
- Add server URL configuration field (pre-filled with default server URL) ✅
- Add server credentials fields (username/password) ✅
- Add toggle switch between direct API calls and server-routed calls ✅
- Add LinkedIn plugin toggle (only enabled when server mode is active) ⏳

#### API Request Logic ✅
- Update the API request mechanism to route through server when enabled ✅
- Forward API keys in request headers/body for stateless operation ✅
- Support both direct and server-routed modes ✅
- Implement error handling with fallback option to direct mode ⏳

#### LinkedIn Integration ⏳
- Add UI elements for LinkedIn plugin interaction ⏳
- Implement API calls to server's LinkedIn plugin endpoint ⏳

### Server Changes

#### Authentication ✅
- Use the existing `/api/v1/auth/token` endpoint for frontend authentication ✅
- Start with predefined credentials (admin/admin123) ✅
- Implement JWT token handling in frontend requests ✅

#### LLM Proxy Endpoints ✅
- Create new endpoints to handle OpenAI API calls ✅
- Create new endpoints to handle Anthropic API calls ✅
- Implement stateless handling of API keys from requests ✅
- Pass provider configuration from frontend to appropriate LLM provider ✅

#### LinkedIn Integration ⏳
- Expose the existing LinkedIn plugin to the frontend ⏳
- Ensure proper authentication and parameter handling ⏳
- Use LinkedIn cookie configured on server initialization ✅

## Current Progress

As of July 20, 2023, we have completed:

1. **Settings Dialog Updates**:
   - Added server URL configuration field
   - Added server credentials fields (username/password)
   - Added toggle switch for server mode

2. **Server-Side Endpoints**:
   - Implemented OpenAI proxy endpoint
   - Implemented Anthropic proxy endpoint
   - Ensured both endpoints match the behavior of direct API calls

3. **Frontend API Integration**:
   - Updated getChatCompletion to support server-routed calls
   - Implemented authentication with the server
   - Added stateless API key forwarding

## Next Steps

1. **Testing** (Current Focus):
   - Test basic LLM API calls routed through the server
   - Verify that server-routed calls behave identically to direct calls

2. **Error Handling**:
   - Implement error handling for server connection failures
   - Add fallback to direct mode when server is unavailable

3. **LinkedIn Integration**:
   - Add LinkedIn plugin toggle to settings
   - Implement LinkedIn plugin API calls from frontend

## User Flow

1. **Configuration**:
   - User enters server URL and credentials in frontend settings
   - User toggles server mode on/off
   - User enables LinkedIn plugin if desired (requires server mode)

2. **Authentication**:
   - Frontend authenticates with server to get JWT token
   - Token is stored in localStorage for subsequent requests
   - Token renewal happens automatically when expired

3. **LLM API Calls**:
   - **Direct Mode**: Call OpenAI/Anthropic APIs directly (current behavior)
   - **Server Mode**: Call server endpoints with API keys in request

4. **LinkedIn Plugin**:
   - Only available when server mode is active
   - Calls server's LinkedIn plugin endpoint with authentication

5. **Error Handling**:
   - If server connection fails, show error popup suggesting to switch to direct mode
   - Provide option to retry or switch modes

## Technical Details

### API Endpoints

#### Server Authentication
```
POST /api/v1/auth/token
Body: { "username": "user", "password": "password" }
Response: { "access_token": "JWT_TOKEN", "token_type": "bearer", "expires_in": 3600 }
```

#### LLM Proxy Endpoints
```
POST /api/v1/llm/openai
Headers: { "Authorization": "Bearer JWT_TOKEN" }
Body: { 
  "api_key": "sk-...",
  "model": "gpt-4",
  "messages": [...] 
}

POST /api/v1/llm/anthropic
Headers: { "Authorization": "Bearer JWT_TOKEN" }
Body: { 
  "api_key": "sk-ant-...",
  "model": "claude-3-opus-20240229",
  "messages": [...] 
}
```

#### LinkedIn Plugin
```
POST /api/v1/plugins/linkedin_external/execute
Headers: { "Authorization": "Bearer JWT_TOKEN" }
Body: {
  "action": "get_profile",
  "parameters": {
    "linkedin_username": "john-doe-123456"
  }
}
```

### Security Considerations

- API keys are sent per-request and not stored on the server
- JWT tokens are stored in localStorage on the client side
- All communication uses HTTPS
- JWT tokens are used for authentication
- Server validates all requests before processing

### Deployment Notes

- Frontend is deployed as an Airtable extension
- Server is deployed separately (e.g., on fly.io)
- Users need to configure the correct server URL in settings

## Implementation Sequence

1. ✅ Frontend settings dialog updates with server URL and toggle
2. ✅ Basic server authentication integration
3. ✅ Server LLM proxy endpoints
4. ✅ Frontend API request logic updates
5. ⏳ Error handling and fallback mechanism
6. ⏳ LinkedIn plugin integration
7. ⏳ Testing and validation

## Testing Plan

1. ✅ Test direct mode (current behavior)
2. ⏳ Test server mode with OpenAI API
3. ⏳ Test server mode with Anthropic API
4. ⏳ Test connection error handling and fallback
5. ⏳ Test LinkedIn plugin functionality
6. ⏳ Test authentication token expiration and renewal 