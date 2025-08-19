// Model pricing data for cost estimation
// UPDATE THESE PRICES REGULARLY - API pricing changes frequently

export interface ModelPricing {
  inputTokensPerK: number; // Cost per 1K input tokens (USD)
  cachedInputTokensPerK?: number; // Cost per 1K cached input tokens (USD), if supported
  outputTokensPerK: number; // Cost per 1K output tokens (USD)
  currency: string;
  lastUpdated: string; // For tracking when prices were last verified
}

/**
 * Current model pricing (in USD per 1K tokens)
 *
 * Check official pricing pages:
 * - OpenAI: https://openai.com/pricing
 * - Anthropic: https://www.anthropic.com/pricing
 */
export const MODEL_PRICING: Record<string, ModelPricing> = {
  // OpenAI Models
  'gpt-4.1': {
    // Successor to GPT-4 Turbo, highly capable
    inputTokensPerK: 0.002, // $2.00 / 1M tokens
    outputTokensPerK: 0.008, // $8.00 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-05-25',
  },
  // (Removed gpt-4o and gpt-4o-mini — no longer supported in UI)
  'gpt-5': {
    // GPT-5 pricing (official)
    // Provided as USD per 1M tokens in the product docs; convert to per-1K values
    inputTokensPerK: 0.00125, // $1.250 / 1M tokens
    cachedInputTokensPerK: 0.000125, // $0.125 / 1M tokens (cached input)
    outputTokensPerK: 0.01, // $10.000 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-08-19',
  },
  'gpt-5-mini': {
    // GPT-5 mini pricing (official)
    inputTokensPerK: 0.00025, // $0.250 / 1M tokens
    cachedInputTokensPerK: 0.000025, // $0.025 / 1M tokens (cached input)
    outputTokensPerK: 0.002, // $2.000 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-08-19',
  },

  // Anthropic Models
  'claude-opus-4-20250514': {
    // Latest most capable model from Anthropic
    inputTokensPerK: 0.015, // $15.00 / 1M tokens
    outputTokensPerK: 0.075, // $75.00 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-05-25',
  },
  'claude-sonnet-4-20250514': {
    // Latest balanced model from Anthropic
    inputTokensPerK: 0.003, // $3.00 / 1M tokens
    outputTokensPerK: 0.015, // $15.00 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-05-25',
  },
  'claude-3-5-haiku-20241022': {
    // Latest fast and cost-effective model from Anthropic
    inputTokensPerK: 0.0008, // $0.80 / 1M tokens
    outputTokensPerK: 0.004, // $4.00 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-05-25',
  },
};

/**
 * Get pricing for a specific model
 * Returns null if model pricing is not found
 */
export const getModelPricing = (modelId: string): ModelPricing | null => {
  return MODEL_PRICING[modelId] || null;
};

/**
 * Format currency amount for display (USD only)
 */
export const formatCurrency = (amount: number): string => {
  return `$${amount.toFixed(3)}`;
};
