# AI Evaluator Extension

> **Note:** This directory contains the frontend Airtable extension component of the Kairos project. For the main project documentation, please see the [main README](../README.md) in the root directory.

---

# ai-evaluator-extension ![deployment automatic](https://img.shields.io/badge/deployment-automatic-success)

[Airtable extension](https://airtable.com/developers/extensions/guides/getting-started) for helping us evaluate applications to our courses using large language models (LLMs).

![Screenshot of the Airtable extension](./screenshot.png)

## Context

We previously manually evaluated each applicant for our educational courses on a set of objective criteria. We would then use these scores plus some additional subjective judgement to come to an application decision. This is time-intensive, and it's difficult to align all the humans to give the same responses for the same person.

In a [previous pilot project](https://github.com/bluedotimpact/ai-application-evaluations-pilot) we concluded that LLMs, while not perfect, could help us automate the first scoring part of our application process.

This repository holds code for an Airtable extension that we can run inside our applications base. We set the relevant inputs (e.g. answers to application questions), the decisioning criteria, and let it evaluate applicants.

## Quick Start

**Simple setup for both OpenAI and Anthropic:**'
1. Install [Bun](https://bun.sh/) with `curl -fsSL https://bun.sh/install | bash`
2. Clone repo, install dependencies: `bun install`
3. **Configure Airtable connection:** Edit `.block/applications.remote.json` with your base and block IDs:
   ```json
   {
     "blockId": "blkYourBlockId",
     "baseId": "appYourBaseId"
   }
   ```
   - **Base ID**: Found in your Airtable base URL - it's the first part after `airtable.com/` (starts with `app`)
   - **Block ID**: Generated when you first create the extension in Airtable (starts with `blk`) - only available during initial creation
4. Run: `bun run start:applications`
5. Configure API and model via settings on the extension page in Airtable
6. ✅ Ready to evaluate! (Uses `gpt-4o-mini` or `claude-3-5-haiku` by default)

## Developer setup

> [Video tutorial](https://drive.google.com/file/d/1b4pouYUZI3HvcEMCCpBXrZ4vr6Ltb6Fi/view?usp=sharing)

> [Legacy video tutorial](https://www.youtube.com/watch?v=nhnPxvEZmLk)

To start developing this extension:

1. Clone this git repository
2. Install [Bun](https://bun.sh/) with `curl -fsSL https://bun.sh/install | bash`
3. Run `bun install`
4. **Configure Airtable connection:** Edit `.block/applications.remote.json` with your base and block IDs:
   ```json
   {
     "blockId": "blkYourBlockId",
     "baseId": "appYourBaseId"
   }
   ```
   - **Base ID**: Found in your Airtable base URL - it's the first part after `airtable.com/` (starts with `app`)
   - **Block ID**: Generated when you first create the extension in Airtable (starts with `blk`) - only available during initial creation
5. Run `bun run start`
6. Load the Airtable base you want to use the tool in
7. Configure the API key and and select a model in the extension settings
8. Make changes to the code and see them reflected in the app!

If the changes don't appear to be updating the app, try clicking the extension name then 'Edit extension', then pasting in the server address printed to the console from step 7 (probably `https://localhost:9000`).

Changes merged into the default branch will automatically be deployed. You can manually deploy new versions using `bun run deploy`. If you get the error `airtableApiBlockNotFound`, set up the block CLI with `npx block set-api-key` with a [personal access token](https://airtable.com/developers/web/guides/personal-access-tokens).

If you want to install this on a new base see [these instructions](https://www.airtable.com/developers/apps/guides/run-in-multiple-bases).

## API Architecture

This extension supports two modes of operation. Choose the one that fits your deployment and governance needs.

- **Non-server (local) usage** — the extension runs entirely in the Airtable client (browser) and calls AI provider APIs directly.
- **Server-based usage** — the extension routes requests through a Kairos MCP server which can perform enrichment (LinkedIn, PDF), multi-axis evaluation, and centralized logging.

### Non-server usage (direct from Airtable)

- Works as the extension currently behaves: direct browser requests to OpenAI and Anthropic.
- No proxy required for OpenAI; Anthropic requires the `anthropic-dangerous-direct-browser-access` header for CORS where applicable.
- Configuration: set your provider, model, and API keys in the extension settings (stored in your Airtable base).
- Pros: simplest setup, keeps data local to your environment. Cons: limited central control and no server-side enrichment.

For additional information on privacy, terms, and the built-in help system see `front/docs/PRIVACY_POLICY.md`, `front/docs/TERMS_OF_SERVICE.md`, and `front/docs/helpSystem.md`.

### Server-based usage (recommended for centralized workflows)

Use server-based mode when you want centralized enrichment, auditing, or to route requests through the MCP server for consistency and additional processing.

Key points:

- **How it works**: The extension sends requests to your MCP server (example: `https://your-mcp-server`) instead of calling provider APIs directly. The MCP server is responsible for calling LLM providers, running plugins (LinkedIn, PDF), and performing multi-axis evaluation.
- **Per-request keys**: The system supports per-request API key behavior — the extension can forward user-supplied provider keys or the server can use its own configured keys depending on your deployment policy.
- **Flags & options**: When running server-based, the extension may pass flags such as `enrichLinkedIn`, `enrichPDF`, and `multiAxis` to control enrichment and scoring behavior. See the server README for the full API and available options (`../server/README.md`).
- **Authentication**: Server mode typically requires the extension to authenticate to the server (JWT or bearer token). Refer to the server documentation for token setup and refresh behavior.
- **Benefits**: centralized logging, controlled prompt templates, consistent model selection, server-side normalization and fallbacks, and plugin-driven enrichment.

- **Available server tools**: The MCP server exposes plugin-based tools such as **PDF resume parsing** and **LinkedIn enrichment/scraping**. These are executed server-side and return structured enrichment data alongside evaluation logs.

For full server API details and deployment instructions, see `../server/README.md`.

### Development Workflow

To run the extension locally in either mode:

```bash
bun run start:applications
# or
bun run start
```

Available scripts:

- `bun run start:applications` - Start the Airtable extension
- `bun run dev` - Alias for `start:applications`
- `bun run deploy` - Deploy a new extension build

### Troubleshooting (common)

- "Failed to fetch":
  - Check network connectivity and provider key validity
  - Verify extension settings and model selection
- Airtable connection issues:
  - Confirm `blockId` and `baseId` in `.block/applications.remote.json`
  - Use the Airtable block CLI (`npx block set-api-key`) if you see `airtableApiBlockNotFound`

## Models and API Keys

Supported models and defaults are defined in `lib/models/config.ts`. Update that file to add or disable models.

Current default models:

- OpenAI default: `gpt-4o-mini`
- Anthropic default: `claude-3-5-haiku-20241022`

To add or update models, edit the `OPENAI_MODELS` and `ANTHROPIC_MODELS` arrays in `lib/models/config.ts`.
