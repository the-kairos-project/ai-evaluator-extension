# Kairos - AI Applicant Evaluation Platform

A comprehensive platform for evaluating applications to educational courses using large language models (LLMs). This repository contains both the frontend Airtable extension and the backend MCP server.

## Repository Structure

- **/front** - Airtable extension for evaluating applications using LLMs
- **/server** - MCP Server for extensible plugin-based AI processing

## Overview

### Frontend (Airtable Extension)

The Airtable extension helps evaluate applicants for educational courses using large language models. It integrates directly with Airtable bases and provides:

- Direct API integration with OpenAI and Anthropic models
- Configurable evaluation criteria and scoring
- Cost estimation and token counting
- Preset management for different evaluation scenarios

### Backend (MCP Server)

The MCP (Multi-Client Platform) Server provides an extensible backend with:

- Semantic routing of requests to appropriate plugins
- Agentic framework with planning and execution capabilities
- Dynamic plugin system with automatic discovery
- External integrations (like LinkedIn data extraction)
- RESTful API with OAuth2 JWT authentication

## Quick Start

### Frontend Setup

1. Install [Bun](https://bun.sh/): `curl -fsSL https://bun.sh/install | bash`
2. Navigate to the frontend directory: `cd front`
3. Install dependencies: `bun install`
4. Configure Airtable connection in `.block/applications.remote.json`
5. Run the extension: `bun run start:applications`
6. Configure API keys in the extension settings

### Server Setup

1. Navigate to the server directory: `cd server`
2. Install dependencies: `poetry install`
3. Configure environment: `cp example.env .env` and edit with your API keys
4. Run the server: `poetry run python -m src.api.main`

### Docker Deployment (Server)

```bash
cd server
docker-compose up -d
```

## Integration Between Components

The frontend extension can be configured to communicate with the MCP Server for advanced processing capabilities:

1. The Airtable extension collects applicant data
2. Data is sent to the MCP Server for processing
3. The MCP Server routes requests to appropriate plugins (LinkedIn, etc.)
4. Results are returned to the extension for display and storage

## Documentation

- [Frontend Documentation](front/README.md)
- [Server Documentation](server/README.md)
- [Contributing Guidelines](server/docs/CONTRIBUTING.md)
- [External MCP Integration](server/docs/integrations/EXTERNAL_MCP_INTEGRATION.md)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 