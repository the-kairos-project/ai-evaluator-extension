# LinkedIn External Plugin

This plugin integrates with an external LinkedIn MCP server to scrape LinkedIn profiles and company pages.

## Features

- Scrape LinkedIn profiles by username or URL
- Scrape company profiles by company name or URL
- Extract structured data from LinkedIn profiles and company pages

## Installation

The plugin requires an external LinkedIn MCP server to be running. This server is included in the `external/linkedin-mcp-server` directory.

To start the LinkedIn MCP server:

```bash
docker-compose up -d linkedin-mcp
```

## Configuration

The plugin requires a valid LinkedIn cookie to authenticate with LinkedIn. This cookie can be provided in several ways:

1. Environment variable: `LINKEDIN_COOKIE`
2. Configuration file: `.env`
3. Runtime configuration when initializing the plugin

## Usage

The plugin is automatically loaded by the MCP server and used when a LinkedIn URL is detected in the `source_url` parameter of an evaluation request.

### Direct API Usage

```python
from src.plugins.linkedin_external_plugin import LinkedInExternalPlugin
from src.core.plugin_system.plugin_interface import PluginRequest

# Initialize plugin
plugin = LinkedInExternalPlugin()
await plugin.initialize({"linkedin_cookie": "your_cookie_here"})

# Create request for profile scraping
request = PluginRequest(
    request_id="test_request",
    action="get_person_profile",
    parameters={"linkedin_username": "john-doe-123456"}
)

# Execute plugin
response = await plugin.execute(request)

# Process response
if response.status == "success":
    profile_data = response.data
    print(f"Name: {profile_data['name']}")
    print(f"Headline: {profile_data['headline']}")
else:
    print(f"Error: {response.error}")
```

### Company Profile Scraping

```python
# Create request for company scraping
request = PluginRequest(
    request_id="test_request",
    action="get_company_profile",
    parameters={
        "company_name": "microsoft",
        "get_employees": False
    }
)

# Execute plugin
response = await plugin.execute(request)
```

## Output Format

The plugin returns structured data in the following format:

### Person Profile

```json
{
  "name": "John Doe",
  "headline": "Software Engineer at Google",
  "location": "San Francisco, CA",
  "about": "Passionate about technology...",
  "experience": [
    {
      "company": "Google",
      "title": "Software Engineer",
      "date_range": "2020 - Present",
      "description": "Working on search algorithms..."
    }
  ],
  "education": [
    {
      "school": "Stanford University",
      "degree": "Master of Science in Computer Science",
      "date_range": "2018 - 2020"
    }
  ],
  "skills": ["Python", "JavaScript", "Machine Learning"],
  "recommendations": [],
  "activities": []
}
```

### Company Profile

```json
{
  "name": "Microsoft",
  "url": "https://www.linkedin.com/company/microsoft",
  "industry": "Computer Software",
  "size": "10,001+ employees",
  "description": "Microsoft Corporation is...",
  "employees": []
}
```