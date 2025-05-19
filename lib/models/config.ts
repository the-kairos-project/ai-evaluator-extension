/**
 * Models configuration file
 * 
 * This file centralizes all model definitions and makes it easy to update them
 * when new models are released or old ones are deprecated.
 */

// Available model providers
export type ModelProvider = 'openai' | 'anthropic';

// Model type definition
export type ModelOption = {
  label: string;
  value: string;
  description: string;
  emoji: string;
  isAvailable: boolean;
};

// OpenAI Models (Updated May 2025)
export const OPENAI_MODELS: ModelOption[] = [
  {
    label: 'GPT-4o',
    value: 'gpt-4o',
    description: 'Latest and most capable multimodal model',
    emoji: '⭐',
    isAvailable: true,
  },
  {
    label: 'GPT-4o mini',
    value: 'gpt-4o-mini',
    description: 'Fast, cost-effective version of GPT-4o',
    emoji: '🚀',
    isAvailable: true,
  },
  {
    label: 'o3mini',
    value: 'gpt-4-o3mini',
    description: 'Next generation, ultra-economical model',
    emoji: '💡',
    isAvailable: true,
  },
];

// Get default OpenAI model
export const DEFAULT_OPENAI_MODEL = OPENAI_MODELS[0].value;

// Anthropic Models (Updated May 2025)
export const ANTHROPIC_MODELS: ModelOption[] = [
  {
    label: 'Claude 3.7 Sonnet',
    value: 'claude-3-7-sonnet-latest',
    description: 'Latest and most powerful Claude model',
    emoji: '✨',
    isAvailable: true,
  },
  {
    label: 'Claude 3.5 Sonnet',
    value: 'claude-3-5-sonnet-20240620',
    description: 'Excellent general purpose model',
    emoji: '🏆',
    isAvailable: true,
  },
  {
    label: 'Claude 3.5 Haiku',
    value: 'claude-3-5-haiku-latest',
    description: 'Fast, economical option',
    emoji: '💨',
    isAvailable: true,
  },
];

// Get default Anthropic model
export const DEFAULT_ANTHROPIC_MODEL = ANTHROPIC_MODELS[0].value;

export const MODEL_PROVIDERS = [
  { 
    id: 'openai',
    name: 'OpenAI',
    emoji: '🤖',
    models: OPENAI_MODELS,
    defaultModel: DEFAULT_OPENAI_MODEL
  },
  {
    id: 'anthropic', 
    name: 'Anthropic Claude',
    emoji: '🧠',
    models: ANTHROPIC_MODELS,
    defaultModel: DEFAULT_ANTHROPIC_MODEL
  }
];

// Get a dictionary of emoji icons for each provider
export const PROVIDER_ICONS: Record<string, string> = {
  openai: '🤖',
  anthropic: '🧠'
};

// Helper function to format a model ID into a user-friendly name
export function formatModelName(modelId: string): string {
  const openAiModel = OPENAI_MODELS.find(model => model.value === modelId);
  if (openAiModel) return openAiModel.label;
  
  const anthropicModel = ANTHROPIC_MODELS.find(model => model.value === modelId);
  if (anthropicModel) return anthropicModel.label;
  
  return modelId;
} 