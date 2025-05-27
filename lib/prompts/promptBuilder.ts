import type { Prompt } from '../getChatCompletion';
// Prompt builder - handles template variable substitution and prompt construction
import type { PromptTemplate, PromptVariables } from './promptTemplates';

export interface PromptConfig {
  template: PromptTemplate;
  variables: PromptVariables;
}

/**
 * Build a complete prompt from template and variables
 */
export const buildPrompt = (applicantData: string, config: PromptConfig): Prompt => {
  const { template, variables } = config;

  // Substitute variables in the system message
  let systemMessage = template.systemMessage
    .replace('{criteriaString}', variables.criteriaString)
    .replace('{rankingKeyword}', variables.rankingKeyword || template.rankingKeyword);

  // Add additional instructions if provided
  if (variables.additionalInstructions?.trim()) {
    systemMessage = systemMessage.replace(
      '{additionalInstructions}',
      `\n\n${variables.additionalInstructions.trim()}`
    );
  } else {
    systemMessage = systemMessage.replace('{additionalInstructions}', '');
  }

  return [
    { role: 'user', content: applicantData },
    { role: 'system', content: systemMessage },
  ];
};

/**
 * Get the ranking keyword for result extraction
 */
export const getRankingKeyword = (config: PromptConfig): string => {
  return config.variables.rankingKeyword || config.template.rankingKeyword;
};
