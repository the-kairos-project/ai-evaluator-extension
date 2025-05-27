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

// Default template - extracted from existing proven prompt
export const ACADEMIC_TEMPLATE: PromptTemplate = {
  id: 'academic',
  name: 'Academic Evaluation',
  description: 'Current proven template for academic/course applications',
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

// Default settings for new installations
export const DEFAULT_PROMPT_SETTINGS = {
  selectedTemplate: ACADEMIC_TEMPLATE.id,
  customTemplate: null as PromptTemplate | null,
  rankingKeyword: ACADEMIC_TEMPLATE.rankingKeyword,
  additionalInstructions: '',
};

// Available templates (starting with just one)
export const AVAILABLE_TEMPLATES: PromptTemplate[] = [ACADEMIC_TEMPLATE];

// Get template by ID with fallback to default
export const getTemplate = (templateId: string): PromptTemplate => {
  return AVAILABLE_TEMPLATES.find((t) => t.id === templateId) || ACADEMIC_TEMPLATE;
};
