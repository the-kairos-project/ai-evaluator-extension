# ai-evaluator-extension ![deployment automatic](https://img.shields.io/badge/deployment-automatic-success)

[Airtable extension](https://airtable.com/developers/extensions/guides/getting-started) for helping us evaluate applications to our courses using large language models (LLMs).

![Screenshot of the Airtable extension](./screenshot.png)

## Context

We previously manually evaluated each applicant for our educational courses on a set of objective criteria. We would then use these scores plus some additional subjective judgement to come to an application decision. This is time-intensive, and it's difficult to align all the humans to give the same responses for the same person.

In a [previous pilot project](https://github.com/bluedotimpact/ai-application-evaluations-pilot) we concluded that LLMs, while not perfect, could help us automate the first scoring part of our application process.

This repository holds code for an Airtable extension that we can run inside our applications base. We set the relevant inputs (e.g. answers to application questions), the decisioning criteria, and let it evaluate applicants.

## Quick Start

**For OpenAI users (simplest setup):**
1. Clone repo, install dependencies: `bun install`
2. Configure API key in `lib/env.ts`
3. Run: `bun run start:applications`
4. ✅ Ready to evaluate! (Uses `gpt-4o-mini` by default)

**For Anthropic users (requires proxy):**
1. Clone repo, install dependencies: `bun install` 
2. Configure API key in `lib/env.ts`
3. Start proxy: `bun run proxy.ts` (keep running)
4. In new terminal: `bun run start:applications`
5. ✅ Ready to evaluate! (Uses `claude-3-5-haiku` by default)

## Developer setup

> [Video tutorial](https://www.youtube.com/watch?v=nhnPxvEZmLk)

To start developing this extension:

1. Clone this git repository
2. Install [Node.js](https://nodejs.org/)
3. Install [Bun](https://bun.sh/) with `curl -fsSL https://bun.sh/install | bash`
4. Run `bun install`
5. Configure API keys and models:
   - Edit `lib/env.ts` with your API keys for OpenAI and/or Anthropic
   - Configure the desired model in `lib/getChatCompletion/openai/config.ts` and/or `lib/getChatCompletion/anthropic/config.ts`
   - Set your OpenAI organization ID if applicable
6. **For Anthropic models only:** Start the proxy server in a separate terminal:
   ```bash
   bun run proxy.ts
   ```
   (Keep this running while using Anthropic models - see [API Architecture](#api-architecture) section below)
7. Run `bun run start` (for the 'Applications' base in the BlueDot Impact AirTable account)
8. Load the relevant base
9. Make changes to the code and see them reflected in the app!

If the changes don't appear to be updating the app, try clicking the extension name then 'Edit extension', then pasting in the server address printed to the console from step 6 (probably `https://localhost:9000`).

Changes merged into the default branch will automatically be deployed. You can manually deploy new versions using `bun run deploy`. If you get the error `airtableApiBlockNotFound`, set up the block CLI with `npx block set-api-key` with a [personal access token](https://airtable.com/developers/web/guides/personal-access-tokens).

**Note:** The deployed extension only includes OpenAI direct API calls. For Anthropic support in production, you'd need to deploy the proxy server to a cloud service (not covered in this setup).

If you want to install this on a new base see [these instructions](https://www.airtable.com/developers/apps/guides/run-in-multiple-bases).

## API Architecture

This extension uses different API architectures for different providers due to CORS (Cross-Origin Resource Sharing) restrictions:

### OpenAI: Direct API Calls ✅
- **No proxy required**
- Calls directly to `https://api.openai.com/v1/chat/completions`
- OpenAI allows cross-origin requests from Airtable extensions
- **Setup**: Just configure your API key - no additional steps needed

### Anthropic: Proxy Server Required 🔄
- **Proxy server required** due to CORS restrictions
- Extension calls `http://localhost:8010/proxy/v1/messages`
- Proxy forwards requests to `https://api.anthropic.com/v1/messages`
- **Setup**: Must run `bun run proxy.ts` before using Anthropic models

### Development Workflow

**Using OpenAI only:**
```bash
bun run start:applications
# That's it! OpenAI works directly
```

**Using Anthropic (or both providers):**
```bash
# Terminal 1: Start the proxy server
bun run proxy.ts

# Terminal 2: Start the extension
bun run start:applications
```

**Available Scripts:**
- `bun run proxy.ts` - Start proxy server for Anthropic
- `bun run start:applications` - Start the Airtable extension
- `bun run dev` - Shows helper message for running both

### Troubleshooting

**"Failed to fetch" error with Anthropic:**
- Ensure the proxy server is running (`bun run proxy.ts`)
- Check that port 8010 is not blocked
- Verify Anthropic API key is configured

**OpenAI works but Anthropic doesn't:**
- This is expected if proxy server isn't running
- Start proxy server and try again

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

#### OpenAI (Direct API - No Proxy Required)
- **GPT-4.1** - Successor to GPT-4 Turbo, highly capable flagship model
- **GPT-4o** - Latest multimodal model with advanced capabilities
- **GPT-4o mini** - Fast, cost-effective version of GPT-4o (default)

#### Anthropic (Requires Proxy Server)  
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
