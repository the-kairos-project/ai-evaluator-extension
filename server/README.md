# MCP Server

> **Note:** This directory contains the backend MCP server component of the Kairos project. For the main project documentation, please see the [main README](../README.md) in the root directory.

---

# MCP Server - Extensible Multi-Client Platform

An intelligent, adaptive, and extensible Multi-Client Platform (MCP) Server that dynamically orchestrates specialized tools and plugins through semantic routing and agentic task planning.

## 🚀 Features

- **Semantic Routing**: LLM-powered intelligent routing of requests to appropriate plugins
- **Agentic Framework**: Planning, execution, and self-correcting reflection loops
- **Dynamic Plugin System**: Hot-reloadable plugins with automatic discovery
- **RESTful API**: FastAPI-based with OAuth2 JWT authentication
- **External Integrations**: Support for external MCP servers (LinkedIn, etc.)
- **PDF Resume Parser**: Extract structured data from PDF resumes

## 📋 Architecture

```
Client → API → Semantic Router → Plugin System → Plugins
                    ↓
             Agentic Framework
```

## 🛠️ Quick Start

### Docker Quick Start (recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/mcp-server.git
cd mcp-server

# Copy example environment and edit required vars
cp example.env .env  # Edit with your API keys and credentials

# Build and start all services (recommended)
docker-compose up --build -d

# Access services
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs (development only)
# - Prometheus: http://localhost:9091
# - Grafana: http://localhost:3000 (admin/admin)
```

### Local Development (alternative)

If you prefer to run the server locally without Docker:

```bash
# Install dependencies and run locally
poetry install
cp example.env .env  # Edit with your API keys
poetry run python -m src.api.main
```

For more deployment and integration details, see the docs in `docs/` (plugins, integrations, multi-axis evaluation).

## 🔌 Plugin Development

Create a new Python file in `src/plugins/`:

```python
from src.core import Plugin, PluginMetadata, PluginRequest, PluginResponse

class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self._metadata = PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            description="My awesome plugin",
            capabilities=["capability1", "capability2"]
        )
    
    async def initialize(self, config=None):
        self._initialized = True
    
    async def execute(self, request: PluginRequest) -> PluginResponse:
        return PluginResponse(
            request_id=request.request_id,
            status="success",
            data={"result": "Hello from my plugin!"}
        )
    
    def get_metadata(self) -> PluginMetadata:
        return self._metadata
```

## 🔐 Authentication

Get a token:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -d "username=admin&password=admin123"
```

Use the token:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/plugins
```

## 📡 API Examples

### Evaluation Endpoint with Enrichment

Evaluate applicants with optional LinkedIn and PDF resume enrichment:

```bash
curl -X POST "http://localhost:8000/api/v1/llm/evaluate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_API_KEY",
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "applicant_data": "Applicant information...",
    "criteria_string": "Evaluation criteria...",
    "use_multi_axis": false,
    "use_plugin": true,
    "source_url": "https://example.com/resume.pdf"
  }'
```

For more details, see [PDF Resume Parser Documentation](docs/plugins/pdf_resume_parser.md).

### Execute a Plugin

```bash
curl -X POST "http://localhost:8000/api/v1/plugins/calculator/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "calculate",
    "parameters": {
      "expression": "5 * (3 + 2)"
    }
  }'
```

### Process a Natural Language Query

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Calculate the area of a circle with radius 5",
    "use_reflection": true
  }'
```

## 📊 Monitoring

Access Grafana dashboards at http://localhost:3000 with default credentials (admin/admin).

Key metrics:
- API performance
- Plugin execution statistics
- System health

## 📚 Documentation

- [Contributing Guidelines](docs/CONTRIBUTING.md)
- [External MCP Integration](docs/integrations/EXTERNAL_MCP_INTEGRATION.md)
- [LinkedIn Plugin](docs/integrations/LINKEDIN_PLUGIN.md)

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](docs/CONTRIBUTING.md) for details on:

- Code style and naming conventions
- Comment guidelines (explain "why" not "what")
- Testing requirements
- Pull request process

Before submitting a PR, run:
```bash
make test lint format
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 