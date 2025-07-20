import { globalConfig } from '@airtable/blocks';
import { env } from '../env';
import {
  DEFAULT_ANTHROPIC_MODEL,
  DEFAULT_OPENAI_MODEL,
  type ModelProvider,
} from '../models/config';

/**
 * Gets the user-selected model provider from global config or defaults to OpenAI
 */
export function getSelectedModelProvider(): ModelProvider {
  const provider = globalConfig.get('selectedModel') as string;

  if (provider === 'anthropic' || provider === 'openai') {
    return provider as ModelProvider;
  }

  return 'openai';
}

/**
 * Gets the OpenAI API key from global config (if set by user) or falls back to env.ts
 */
export function getOpenAiApiKey(): string {
  const configKey = globalConfig.get('openAiApiKey') as string;
  return configKey || env.OPENAI_API_KEY;
}

/**
 * Gets the Anthropic API key from global config (if set by user) or falls back to env.ts
 */
export function getAnthropicApiKey(): string {
  const configKey = globalConfig.get('anthropicApiKey') as string;
  return configKey || env.ANTHROPIC_API_KEY;
}

/**
 * Gets the OpenAI model name from global config or falls back to default
 */
export function getOpenAiModelName(): string {
  const modelName = globalConfig.get('openAiModel') as string;
  return modelName || DEFAULT_OPENAI_MODEL;
}

/**
 * Gets the Anthropic model name from global config or falls back to default
 */
export function getAnthropicModelName(): string {
  const modelName = globalConfig.get('anthropicModel') as string;
  return modelName || DEFAULT_ANTHROPIC_MODEL;
}
