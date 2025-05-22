// Main cost estimator - combines token counting and pricing
import type { TokenCount } from './tokenCounter';
import { estimateBatchTokens, estimateEvaluationTokens } from './tokenCounter';
import { getModelPricing, convertCurrency, formatCurrency } from './pricing';
import { getPromptSettings, getActiveTemplate } from '../prompts';

export interface CostEstimate {
  tokenBreakdown: TokenCount;
  costUSD: number;
  costLocal: number;
  currency: string;
  modelUsed: string;
  breakdown: {
    inputCost: number;
    outputCost: number;
    totalEvaluations: number;
  };
  warnings: string[];
}

/**
 * Calculate cost estimate for a batch of evaluations
 */
export const estimateBatchCost = (
  applicants: Record<string, string>[],
  evaluationFields: Array<{ criteria: string }>,
  selectedModel: string,
  targetCurrency: string = 'USD'
): CostEstimate => {
  const warnings: string[] = [];
  
  // Get current prompt settings
  const promptSettings = getPromptSettings();
  const template = getActiveTemplate();
  
  // Get model pricing
  const pricing = getModelPricing(selectedModel);
  if (!pricing) {
    warnings.push(`Pricing not found for model ${selectedModel}. Using GPT-4o estimates.`);
    // Fallback to GPT-4o pricing if model not found
    const fallbackPricing = getModelPricing('gpt-4o');
    if (!fallbackPricing) {
      throw new Error('No pricing data available for cost estimation');
    }
  }
  
  const modelPricing = pricing || getModelPricing('gpt-4o')!;
  
  // Calculate token usage
  const tokenBreakdown = estimateBatchTokens(
    applicants,
    evaluationFields,
    template.systemMessage,
    promptSettings.additionalInstructions
  );
  
  // Calculate costs
  const inputCostUSD = (tokenBreakdown.inputTokens / 1000) * modelPricing.inputTokensPerK;
  const outputCostUSD = (tokenBreakdown.outputTokens / 1000) * modelPricing.outputTokensPerK;
  const totalCostUSD = inputCostUSD + outputCostUSD;
  
  // Convert to target currency
  const totalCostLocal = convertCurrency(totalCostUSD, targetCurrency);
  
  // Add warnings for expensive operations
  if (totalCostUSD > 10) {
    warnings.push(`High cost estimate: ${formatCurrency(totalCostUSD, 'USD')}. Consider testing with fewer evaluations first.`);
  }
  
  if (tokenBreakdown.totalTokens > 1000000) {
    warnings.push(`Very high token usage: ${tokenBreakdown.totalTokens.toLocaleString()} tokens. This may take significant time.`);
  }
  
  const totalEvaluations = applicants.length * evaluationFields.length;
  if (totalEvaluations > 100) {
    warnings.push(`Large batch: ${totalEvaluations} evaluations. Consider running in smaller batches.`);
  }
  
  return {
    tokenBreakdown,
    costUSD: totalCostUSD,
    costLocal: totalCostLocal,
    currency: targetCurrency,
    modelUsed: selectedModel,
    breakdown: {
      inputCost: convertCurrency(inputCostUSD, targetCurrency),
      outputCost: convertCurrency(outputCostUSD, targetCurrency),
      totalEvaluations
    },
    warnings
  };
};

/**
 * Calculate cost estimate for a single evaluation (for preview/testing)
 */
export const estimateSingleCost = (
  applicantData: Record<string, string>,
  criteria: string,
  selectedModel: string,
  targetCurrency: string = 'USD'
): CostEstimate => {
  const warnings: string[] = [];
  
  // Get current prompt settings
  const promptSettings = getPromptSettings();
  const template = getActiveTemplate();
  
  // Get model pricing
  const pricing = getModelPricing(selectedModel);
  if (!pricing) {
    warnings.push(`Pricing not found for model ${selectedModel}. Using GPT-4o estimates.`);
  }
  
  const modelPricing = pricing || getModelPricing('gpt-4o')!;
  
  // Calculate token usage for single evaluation
  const tokenBreakdown = estimateEvaluationTokens(
    applicantData,
    template.systemMessage,
    criteria,
    promptSettings.additionalInstructions
  );
  
  // Calculate costs
  const inputCostUSD = (tokenBreakdown.inputTokens / 1000) * modelPricing.inputTokensPerK;
  const outputCostUSD = (tokenBreakdown.outputTokens / 1000) * modelPricing.outputTokensPerK;
  const totalCostUSD = inputCostUSD + outputCostUSD;
  
  // Convert to target currency
  const totalCostLocal = convertCurrency(totalCostUSD, targetCurrency);
  
  return {
    tokenBreakdown,
    costUSD: totalCostUSD,
    costLocal: totalCostLocal,
    currency: targetCurrency,
    modelUsed: selectedModel,
    breakdown: {
      inputCost: convertCurrency(inputCostUSD, targetCurrency),
      outputCost: convertCurrency(outputCostUSD, targetCurrency),
      totalEvaluations: 1
    },
    warnings
  };
};

/**
 * Format cost estimate for display
 */
export const formatCostEstimate = (estimate: CostEstimate): string => {
  const { tokenBreakdown, costLocal, currency, breakdown, warnings } = estimate;
  
  let result = `${breakdown.totalEvaluations} evaluation${breakdown.totalEvaluations > 1 ? 's' : ''}: `;
  result += `${tokenBreakdown.totalTokens.toLocaleString()} tokens `;
  result += `≈ ${formatCurrency(costLocal, currency)}`;
  
  if (warnings.length > 0) {
    result += `\n⚠️ ${warnings[0]}`;
  }
  
  return result;
}; 