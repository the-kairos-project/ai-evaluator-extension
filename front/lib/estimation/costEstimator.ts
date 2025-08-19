import { formatCurrency, getModelPricing } from './pricing';

export interface TokenBreakdown {
  inputTokens: number;
  outputTokens: number;
  model: string;
}

export interface CostEstimate {
  costUSD: number;
  costLocal: number;
  currency: string;
  tokenBreakdown: TokenBreakdown[];
  breakdown: {
    inputCost: number;
    outputCost: number;
  };
  warnings: string[];
}

/**
 * Estimate the cost of evaluating multiple entries
 * @param estimatedInputTokens Average tokens per entry for input
 * @param estimatedOutputTokens Average tokens per entry for output
 * @param numberOfEntries Number of entries to evaluate
 * @param modelId Model identifier (e.g., 'gpt-5-mini', 'claude-3-5-haiku-20241022')
 * @returns Cost estimate with token and cost breakdown
 */
export const estimateCost = (
  estimatedInputTokens: number,
  estimatedOutputTokens: number,
  numberOfEntries: number,
  modelId: string
): CostEstimate => {
  const pricing = getModelPricing(modelId);
  if (!pricing) {
    throw new Error(`No pricing data available for model: ${modelId}`);
  }

  const warnings: string[] = [];

  // Calculate total tokens
  const totalInputTokens = estimatedInputTokens * numberOfEntries;
  const totalOutputTokens = estimatedOutputTokens * numberOfEntries;

  // Calculate costs (pricing is per 1K tokens)
  const inputCostUSD = (totalInputTokens / 1000) * pricing.inputTokensPerK;
  const outputCostUSD = (totalOutputTokens / 1000) * pricing.outputTokensPerK;
  const totalCostUSD = inputCostUSD + outputCostUSD;

  // Add warnings for high costs
  if (totalCostUSD > 10) {
    warnings.push(
      `High cost estimate: ${formatCurrency(totalCostUSD)}. Consider testing with fewer evaluations first.`
    );
  }

  // Prepare token breakdown for display
  const tokenBreakdown: TokenBreakdown[] = [
    {
      inputTokens: totalInputTokens,
      outputTokens: totalOutputTokens,
      model: modelId,
    },
  ];

  return {
    costUSD: totalCostUSD,
    costLocal: totalCostUSD,
    currency: 'USD',
    tokenBreakdown,
    breakdown: {
      inputCost: inputCostUSD,
      outputCost: outputCostUSD,
    },
    warnings,
  };
};

/**
 * Estimate the cost of a single evaluation
 * @param estimatedInputTokens Tokens for input
 * @param estimatedOutputTokens Tokens for output
 * @param modelId Model identifier
 * @returns Cost estimate for a single evaluation
 */
export const estimateSingleCost = (
  estimatedInputTokens: number,
  estimatedOutputTokens: number,
  modelId: string
): CostEstimate => {
  const pricing = getModelPricing(modelId);
  if (!pricing) {
    throw new Error(`No pricing data available for model: ${modelId}`);
  }

  const warnings: string[] = [];

  // Calculate costs (pricing is per 1K tokens)
  const inputCostUSD = (estimatedInputTokens / 1000) * pricing.inputTokensPerK;
  const outputCostUSD = (estimatedOutputTokens / 1000) * pricing.outputTokensPerK;
  const totalCostUSD = inputCostUSD + outputCostUSD;

  // Prepare token breakdown for display
  const tokenBreakdown: TokenBreakdown[] = [
    {
      inputTokens: estimatedInputTokens,
      outputTokens: estimatedOutputTokens,
      model: modelId,
    },
  ];

  return {
    costUSD: totalCostUSD,
    costLocal: totalCostUSD,
    currency: 'USD',
    tokenBreakdown,
    breakdown: {
      inputCost: inputCostUSD,
      outputCost: outputCostUSD,
    },
    warnings,
  };
};

/**
 * Format cost estimate for display
 */
export const formatCostEstimate = (estimate: CostEstimate): string => {
  const { tokenBreakdown, costLocal, breakdown, warnings } = estimate;

  let result = '';

  // Add cost information
  result += `≈ ${formatCurrency(costLocal)}`;

  // Add breakdown if helpful
  if (breakdown.inputCost > 0 || breakdown.outputCost > 0) {
    result += ` (${formatCurrency(breakdown.inputCost)} input + ${formatCurrency(breakdown.outputCost)} output)`;
  }

  // Add token information
  if (tokenBreakdown.length === 1) {
    const tb = tokenBreakdown[0];
    result += ` • ${tb.inputTokens.toLocaleString()} input + ${tb.outputTokens.toLocaleString()} output tokens`;
  }

  // Add warnings
  if (warnings.length > 0) {
    result += `\n⚠️ ${warnings.join('\n⚠️ ')}`;
  }

  return result;
};

/**
 * Backwards-compatible wrapper for batch cost estimation
 * @deprecated Use estimateCost directly with token estimates
 */
export const estimateBatchCost = (
  applicants: Record<string, string>[],
  evaluationFields: Array<{ criteria: string }>,
  modelId: string
): CostEstimate => {
  // Simple estimation based on data length - this is a rough approximation
  const avgInputTokens = 500; // Average tokens per evaluation input
  const avgOutputTokens = 100; // Average tokens per evaluation output
  const totalEvaluations = applicants.length * evaluationFields.length;

  return estimateCost(avgInputTokens, avgOutputTokens, totalEvaluations, modelId);
};
