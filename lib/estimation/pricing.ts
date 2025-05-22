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
 * ⚠️  TODO: UPDATE THESE PRICES WITH CURRENT RATES
 * Check official pricing pages:
 * - OpenAI: https://openai.com/pricing
 * - Anthropic: https://www.anthropic.com/pricing
 */
export const MODEL_PRICING: Record<string, ModelPricing> = {
  // OpenAI Models
  'gpt-4o': {
    inputTokensPerK: 0.005,   // TODO: Verify current GPT-4o pricing
    outputTokensPerK: 0.015,  // TODO: Verify current GPT-4o pricing
    currency: 'USD',
    lastUpdated: '2024-01-XX' // TODO: Update with verification date
  },
  
  'gpt-4o-mini': {
    inputTokensPerK: 0.00015, // TODO: Verify current GPT-4o-mini pricing
    outputTokensPerK: 0.0006, // TODO: Verify current GPT-4o-mini pricing
    currency: 'USD',
    lastUpdated: '2024-01-XX' // TODO: Update with verification date
  },
  
  'gpt-4-turbo': {
    inputTokensPerK: 0.01,    // TODO: Verify current GPT-4-turbo pricing
    outputTokensPerK: 0.03,   // TODO: Verify current GPT-4-turbo pricing
    currency: 'USD',
    lastUpdated: '2024-01-XX' // TODO: Update with verification date
  },
  
  'gpt-4': {
    inputTokensPerK: 0.03,    // TODO: Verify current GPT-4 pricing
    outputTokensPerK: 0.06,   // TODO: Verify current GPT-4 pricing
    currency: 'USD',
    lastUpdated: '2024-01-XX' // TODO: Update with verification date
  },
  
  'gpt-3.5-turbo': {
    inputTokensPerK: 0.0015,  // TODO: Verify current GPT-3.5-turbo pricing
    outputTokensPerK: 0.002,  // TODO: Verify current GPT-3.5-turbo pricing
    currency: 'USD',
    lastUpdated: '2024-01-XX' // TODO: Update with verification date
  },
  
  // Anthropic Models
  'claude-3-5-sonnet-20241022': {
    inputTokensPerK: 0.003,   // TODO: Verify current Claude 3.5 Sonnet pricing
    outputTokensPerK: 0.015,  // TODO: Verify current Claude 3.5 Sonnet pricing
    currency: 'USD',
    lastUpdated: '2024-01-XX' // TODO: Update with verification date
  },
  
  'claude-3-5-haiku-20241022': {
    inputTokensPerK: 0.001,   // TODO: Verify current Claude 3.5 Haiku pricing
    outputTokensPerK: 0.005,  // TODO: Verify current Claude 3.5 Haiku pricing
    currency: 'USD',
    lastUpdated: '2024-01-XX' // TODO: Update with verification date
  },
  
  'claude-3-opus-20240229': {
    inputTokensPerK: 0.015,   // TODO: Verify current Claude 3 Opus pricing
    outputTokensPerK: 0.075,  // TODO: Verify current Claude 3 Opus pricing
    currency: 'USD',
    lastUpdated: '2024-01-XX' // TODO: Update with verification date
  },
  
  'claude-3-sonnet-20240229': {
    inputTokensPerK: 0.003,   // TODO: Verify current Claude 3 Sonnet pricing
    outputTokensPerK: 0.015,  // TODO: Verify current Claude 3 Sonnet pricing
    currency: 'USD',
    lastUpdated: '2024-01-XX' // TODO: Update with verification date
  },
  
  'claude-3-haiku-20240307': {
    inputTokensPerK: 0.00025, // TODO: Verify current Claude 3 Haiku pricing
    outputTokensPerK: 0.00125,// TODO: Verify current Claude 3 Haiku pricing
    currency: 'USD',
    lastUpdated: '2024-01-XX' // TODO: Update with verification date
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
 * TODO: Consider using a real-time currency API for accurate conversion
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