import { getOpenAiApiKey, getOpenAiModelName } from '../apiKeyManager';

// Use the API key manager to get the key (from config or env.ts)
export const openAiApiKey = getOpenAiApiKey();
export const openAiOrganisation = ''; // Organization ID is optional
// Get model name from global config or fall back to default
export const openAiModel = getOpenAiModelName();
// Maximum number of open requests at any one time. Higher = faster, but more likely to hit rate limits.
export const openAiRequestConcurrency = 30;
