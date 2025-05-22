import { getAnthropicApiKey, getAnthropicModelName } from '../apiKeyManager';

// Use the API key manager to get the key (from config or env.ts)
export const anthropicApiKey = getAnthropicApiKey();
// Get model name from global config or fall back to default
export const anthropicModel = getAnthropicModelName();
