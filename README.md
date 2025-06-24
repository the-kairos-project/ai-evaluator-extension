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

> [Video tutorial](https://www.youtube.com/watch?v=nhnPxvEZmLk)

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

This extension now uses direct API calls for both OpenAI and Anthropic providers:

### OpenAI: Direct API Calls ✅
- **No proxy required**
- Calls directly to `https://api.openai.com/v1/chat/completions`
- OpenAI allows cross-origin requests from Airtable extensions
- **Setup**: Just configure your API key - no additional steps needed

### Anthropic: Direct API Calls ✅
- **No proxy required** (updated with direct browser access)
- Calls directly to `https://api.anthropic.com/v1/messages`
- Uses `anthropic-dangerous-direct-browser-access: true` header for CORS
- **Setup**: Just configure your API key - no additional steps needed

### Development Workflow

**For both OpenAI and Anthropic:**
```bash
bun run start:applications
# That's it! Both providers work directly now
```

**Available Scripts:**
- `bun run start:applications` - Start the Airtable extension
- `bun run dev` - Same as start:applications

### Troubleshooting

**"Failed to fetch" error:**
- Check your internet connection
- Verify your API keys are configured correctly in `lib/env.ts`
- Ensure your API keys have sufficient credits/permissions

**Airtable connection issues:**
- Verify your `blockId` and `baseId` are correct in `.block/applications.remote.json`
- Ensure the Block ID starts with `blk` and Base ID starts with `app`
- Make sure you have access permissions to the Airtable base
- Try refreshing the Airtable page and restarting the development server

## Models and API Keys

This extension supports both OpenAI and Anthropic Claude models. You can configure:

1. Which AI provider to use (OpenAI or Anthropic Claude)
2. Which specific model to use for each provider
3. API keys for both providers

The application has a centralized model configuration system located in `lib/models/config.ts`. This makes it easy to:

- Add new models when providers release them
- Update model parameters when providers change them
- Mark models as unavailable if needed

### Supported Models

#### OpenAI (Direct API)
- **GPT-4.1** - Successor to GPT-4 Turbo, highly capable flagship model
- **GPT-4o** - Latest multimodal model with advanced capabilities
- **GPT-4o mini** - Fast, cost-effective version of GPT-4o (default)

#### Anthropic (Direct API)
- **Claude Opus 4** - Latest most capable model from Anthropic
- **Claude Sonnet 4** - Latest balanced model from Anthropic
- **Claude 3.5 Haiku** - Latest fast and cost-effective model from Anthropic (default)

**Default Models:**
- OpenAI: `gpt-4o-mini` (cost-effective and fast)
- Anthropic: `claude-3-5-haiku-20241022` (cost-effective and fast)

### Updating Models

To add or update models, modify the `OPENAI_MODELS` and `ANTHROPIC_MODELS` arrays in `lib/models/config.ts`. Each model requires:

- `label`: Display name
- `value`: API identifier
- `description`: Short description
- `emoji`: Representative emoji
- `isAvailable`: Whether this model is available
