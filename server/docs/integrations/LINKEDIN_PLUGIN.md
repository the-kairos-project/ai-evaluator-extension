# LinkedIn Plugin Documentation

## Quick Start

```bash
# 1. Set LinkedIn cookie
export LINKEDIN_COOKIE="your_li_at_cookie_value"

# 2. Start services
docker-compose up -d

# 3. Get authentication token
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -d "username=admin&password=admin123"

# 4. Query LinkedIn profile
curl -X POST "http://localhost:8000/api/v1/plugins/linkedin_external/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "get_profile",
    "parameters": {
      "linkedin_username": "john-doe-123456"
    }
  }'
```

## Overview

The LinkedIn plugin integrates with the [LinkedIn MCP Server](https://github.com/stickerdaniel/linkedin-mcp-server) to provide LinkedIn profile and company scraping capabilities. This plugin follows a single-cookie architecture where the LinkedIn authentication cookie is set at server startup and used for all requests.

For detailed implementation information, see [External MCP Integration Pattern](EXTERNAL_MCP_INTEGRATION.md).

## Architecture

### Single Cookie Design

The LinkedIn MCP Server is designed to:
1. Accept a LinkedIn cookie (`li_at`) at startup
2. Create and maintain a Chrome WebDriver session logged into LinkedIn
3. Use this single session for all scraping requests

This means:
- **One cookie per server instance**: All requests to the LinkedIn plugin use the same cookie
- **Cookie cannot be changed per request**: To use a different cookie, you must restart the server
- **Cookie is required at startup**: The plugin will not load without a valid cookie

### Integration Flow

```
1. Server Startup
   ├── Read LINKEDIN_COOKIE from environment
   ├── Start LinkedIn MCP Server with cookie
   ├── LinkedIn MCP Server logs into LinkedIn
   └── Session ready for all requests

2. API Request
   ├── Client sends request (no cookie needed)
   ├── MCP Server routes to LinkedIn plugin
   ├── LinkedIn plugin calls LinkedIn MCP Server
   └── LinkedIn MCP Server uses existing session
```

## Configuration

### Environment Variables

Set the LinkedIn cookie before starting the server:

```bash
export LINKEDIN_COOKIE="your_li_at_cookie_value"
```

### Docker Compose

The cookie is passed to both containers:

```yaml
services:
  mcp-server:
    environment:
      - LINKEDIN_COOKIE=${LINKEDIN_COOKIE}
  
  linkedin-mcp:
    environment:
      - LINKEDIN_COOKIE=${LINKEDIN_COOKIE}
```

## Getting the LinkedIn Cookie

### Option 1: Browser Developer Tools

1. Log into LinkedIn in your browser
2. Open Developer Tools (F12)
3. Go to Application → Cookies → www.linkedin.com
4. Find the `li_at` cookie
5. Copy the value (just the value, not "li_at=")

### Option 2: Using the LinkedIn MCP Server

```bash
docker run -it --rm \
  stickerdaniel/linkedin-mcp-server:latest \
  --get-cookie
```

## Usage

### API Endpoints

**Get LinkedIn Profile:**
```bash
curl -X POST http://localhost:8000/api/v1/plugins/linkedin_external/execute \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "get_profile",
    "parameters": {
      "linkedin_username": "john-doe-123456"
    }
  }'
```

**Get Company Profile:**
```bash
curl -X POST http://localhost:8000/api/v1/plugins/linkedin_external/execute \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "get_company",
    "parameters": {
      "company_name": "microsoft",
      "get_employees": false
    }
  }'
```

### Response Structure

Profile response example:

```json
{
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "success",
  "data": {
    "name": "John Doe",
    "job_title": "Software Engineer",
    "company": "Example Corp",
    "about": "Experienced software engineer with...",
    "experiences": [
      {
        "position_title": "Software Engineer",
        "company": "Example Corp",
        "from_date": "Jan 2022",
        "to_date": "Present",
        "duration": "1 yr 6 mos",
        "location": "San Francisco, CA",
        "description": "Developing cloud-native applications..."
      }
    ],
    "educations": [
      {
        "institution": "Stanford University",
        "degree": "Master of Science - Computer Science",
        "from_date": "2018",
        "to_date": "2020",
        "description": "Specialization in Machine Learning"
      }
    ],
    "open_to_work": false
  },
  "metadata": {
    "external_tool": "get_person_profile",
    "external_server": "http://linkedin-mcp:8080",
    "action_performed": "get_profile"
  }
}
```

## Important Notes

1. **Cookie Expiration**: LinkedIn cookies expire after ~30 days. When expired, you'll need to get a new cookie and restart the server.

2. **Rate Limiting**: LinkedIn may rate limit or require CAPTCHA if too many requests are made. Use responsibly.

3. **Single Session**: Only one LinkedIn session can be active per cookie. Don't use the same cookie in multiple places simultaneously.

4. **No Per-Request Cookies**: The current architecture doesn't support different cookies for different requests. All requests use the server's startup cookie.

## Troubleshooting

### Plugin Not Loading

If you see "LinkedIn plugin not loaded" in the logs:
- Ensure `LINKEDIN_COOKIE` environment variable is set
- Check the cookie format (should not include "li_at=" prefix)
- Verify the cookie is still valid

### Authentication Failed

If you see "Cookie authentication failed":
- The cookie may have expired
- You may be using the cookie in multiple places
- LinkedIn may require re-authentication

### Session Issues

If requests fail after server has been running:
- The LinkedIn session may have timed out
- Restart the server to create a new session
- Consider implementing periodic health checks

## Future Improvements

Potential enhancements for multi-cookie support:

1. **Session Pool**: Maintain multiple LinkedIn sessions with different cookies
2. **Per-Request Routing**: Route requests to appropriate session based on criteria
3. **Dynamic Sessions**: Create new sessions on-demand with provided cookies
4. **Cookie Rotation**: Automatically rotate between multiple cookies 