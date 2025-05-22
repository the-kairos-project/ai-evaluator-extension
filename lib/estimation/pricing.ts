// Model pricing data for cost estimation
// UPDATE THESE PRICES REGULARLY - API pricing changes frequently

export interface ModelPricing {
  inputTokensPerK: number;  // Cost per 1K input tokens (USD)
  outputTokensPerK: number; // Cost per 1K output tokens (USD)
  currency: string;
  lastUpdated: string;      // For tracking when prices were last verified
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
  'gpt-4.1': { // Successor to GPT-4 Turbo, highly capable
    inputTokensPerK: 0.002,   // $2.00 / 1M tokens
    outputTokensPerK: 0.008,  // $8.00 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-05-25'
  },
  'gpt-4o': {
    inputTokensPerK: 0.0025,  // $2.50 / 1M tokens
    outputTokensPerK: 0.01,   // $10.00 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-05-25'
  },
  'gpt-4o-mini': {
    inputTokensPerK: 0.00015, // $0.15 / 1M tokens
    outputTokensPerK: 0.0006, // $0.60 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-05-25'
  },

  // Anthropic Models
  'claude-opus-4-20250514': { // Latest most capable model from Anthropic
    inputTokensPerK: 0.015,   // $15.00 / 1M tokens
    outputTokensPerK: 0.075,  // $75.00 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-05-25'
  },
  'claude-sonnet-4-20250514': { // Latest balanced model from Anthropic
    inputTokensPerK: 0.003,   // $3.00 / 1M tokens
    outputTokensPerK: 0.015,  // $15.00 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-05-25'
  },
  'claude-3-5-haiku-20241022': { // Latest fast and cost-effective model from Anthropic
    inputTokensPerK: 0.0008,  // $0.80 / 1M tokens
    outputTokensPerK: 0.004,  // $4.00 / 1M tokens
    currency: 'USD',
    lastUpdated: '2025-05-25'
  }
};

/**
 * Get pricing for a specific model
 * Returns null if model pricing is not found
 */
export const getModelPricing = (modelId: string): ModelPricing | null => {
  return MODEL_PRICING[modelId] || null;
};

/**
 * Convert USD to other currencies (approximate rates)
 */
export const convertCurrency = (usdAmount: number, targetCurrency: string): number => {
  const exchangeRates = {
    'USD': 1.0,
    'GBP': 0.79,  // TODO: Update with current USD to GBP rate
    'EUR': 0.92,  // TODO: Update with current USD to EUR rate
    'CAD': 1.35,  // TODO: Update with current USD to CAD rate
  };
  
  const rate = exchangeRates[targetCurrency as keyof typeof exchangeRates] || 1.0;
  return usdAmount * rate;
};

/**
 * Format currency amount for display
 */
export const formatCurrency = (amount: number, currency: string = 'USD'): string => {
  const symbols = {
    'USD': '$',
    'GBP': '£',
    'EUR': '€',
    'CAD': 'C$'
  };
  
  const symbol = symbols[currency as keyof typeof symbols] || currency;
  return `${symbol}${amount.toFixed(3)}`;
}; 