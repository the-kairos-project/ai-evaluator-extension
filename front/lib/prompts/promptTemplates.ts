// Prompt template system for AI evaluations
// This file contains all prompt templates and their configurations

export interface PromptTemplate {
  id: string;
  name: string;
  description: string;
  systemMessage: string;
  rankingKeyword: string;
  additionalInstructions?: string;
}

export interface PromptVariables {
  criteriaString: string;
  rankingKeyword?: string;
  additionalInstructions?: string;
}

// SPAR Single-Axis Template - derived from SPAR first axis (General Promise)
// This is the default single-axis evaluation template when multi-axis is disabled
export const SPAR_SINGLE_AXIS_TEMPLATE: PromptTemplate = {
  id: 'spar_single',
  name: 'General Promise Evaluation',
  description: 'Single-axis evaluation using SPAR General Promise criteria',
  systemMessage: `Evaluate the application above, based on the following rubric: {criteriaString}

You should ignore general statements or facts about the world, and focus on what the applicant themselves has achieved. You do not need to structure your assessment similar to the answers the user has given.

IMPORTANT RATING CONSTRAINTS:
- Your rating MUST be an integer (whole number only)
- Your rating MUST be between 1 and 5 (inclusive)
- DO NOT use ratings above 5 or below 1
- If the rubric mentions different scale values, convert them to the 1-5 scale

First explain your reasoning thinking step by step. Then output your final answer by stating '{rankingKeyword} = ' and then the relevant integer between 1 and 5.{additionalInstructions}`,
  rankingKeyword: 'FINAL_RANKING',
  additionalInstructions: '',
};

// Legacy template alias for backward compatibility
// @deprecated Use SPAR_SINGLE_AXIS_TEMPLATE instead
export const ACADEMIC_TEMPLATE = SPAR_SINGLE_AXIS_TEMPLATE;

// Default settings for new installations
export const DEFAULT_PROMPT_SETTINGS = {
  selectedTemplate: SPAR_SINGLE_AXIS_TEMPLATE.id,
  customTemplate: null as PromptTemplate | null,
  rankingKeyword: SPAR_SINGLE_AXIS_TEMPLATE.rankingKeyword,
  additionalInstructions: '',
};

// Available templates
export const AVAILABLE_TEMPLATES: PromptTemplate[] = [SPAR_SINGLE_AXIS_TEMPLATE];

// Get template by ID with fallback to default
export const getTemplate = (templateId: string): PromptTemplate => {
  return AVAILABLE_TEMPLATES.find((t) => t.id === templateId) || SPAR_SINGLE_AXIS_TEMPLATE;
};
