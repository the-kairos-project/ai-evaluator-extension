// Token counter for cost estimation
// Provides approximate token counts for different content types

/**
 * Approximate token counting for cost estimation
 * Note: This is an approximation - actual tokens may vary by ~10-20%
 */

export interface TokenCount {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
}

/**
 * Estimate tokens in text (rough approximation)
 * Rule of thumb: ~4 characters per token for English text
 */
export const estimateTokens = (text: string): number => {
  if (!text) return 0;
  
  // Remove extra whitespace and count characters
  const cleanText = text.trim().replace(/\s+/g, ' ');
  
  // Approximate: 4 characters per token (conservative estimate)
  // This accounts for common English text patterns
  return Math.ceil(cleanText.length / 4);
};

/**
 * Estimate tokens for a single evaluation (one applicant, one criteria)
 */
export const estimateEvaluationTokens = (
  applicantData: Record<string, string>,
  promptTemplate: string,
  criteria: string,
  additionalInstructions?: string
): TokenCount => {
  // Count applicant data tokens
  const applicantText = Object.values(applicantData)
    .filter(value => value && value.trim())
    .join('\n\n');
  const applicantTokens = estimateTokens(applicantText);
  
  // Count system prompt tokens (template + criteria + instructions)
  const systemPrompt = promptTemplate
    .replace('{criteriaString}', criteria)
    .replace('{additionalInstructions}', additionalInstructions || '');
  const promptTokens = estimateTokens(systemPrompt);
  
  // Total input tokens
  const inputTokens = applicantTokens + promptTokens;
  
  // Estimate output tokens (AI response)
  // Make output estimate more realistic based on criteria complexity
  const criteriaTokens = estimateTokens(criteria);
  
  // Base output: 150-300 tokens for simple evaluations
  // Add tokens based on criteria complexity
  // More complex criteria = longer explanations
  let outputTokens = 200; // Base response
  
  if (criteriaTokens > 100) {
    outputTokens += Math.min(300, criteriaTokens * 2); // Complex criteria = longer response
  } else if (criteriaTokens > 50) {
    outputTokens += 100; // Medium criteria = medium response
  } else {
    outputTokens += 50; // Simple criteria = short response
  }
  
  // Conservative upper bound
  outputTokens = Math.min(outputTokens, 600);
  
  return {
    inputTokens,
    outputTokens,
    totalTokens: inputTokens + outputTokens
  };
};

/**
 * Estimate tokens for multiple evaluations
 */
export const estimateBatchTokens = (
  applicants: Record<string, string>[],
  evaluationFields: Array<{ criteria: string }>,
  promptTemplate: string,
  additionalInstructions?: string
): TokenCount => {
  let totalInputTokens = 0;
  let totalOutputTokens = 0;
  
  // Calculate for each applicant × evaluation field combination
  for (const applicant of applicants) {
    for (const field of evaluationFields) {
      const tokens = estimateEvaluationTokens(
        applicant,
        promptTemplate,
        field.criteria,
        additionalInstructions
      );
      
      totalInputTokens += tokens.inputTokens;
      totalOutputTokens += tokens.outputTokens;
    }
  }
  
  return {
    inputTokens: totalInputTokens,
    outputTokens: totalOutputTokens,
    totalTokens: totalInputTokens + totalOutputTokens
  };
}; 