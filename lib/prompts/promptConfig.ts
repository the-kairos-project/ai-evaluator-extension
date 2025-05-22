// Prompt configuration manager - handles loading/saving prompt settings
import { globalConfig } from '@airtable/blocks';
import type { PromptTemplate } from './promptTemplates';
import { ACADEMIC_TEMPLATE, DEFAULT_PROMPT_SETTINGS, getTemplate } from './promptTemplates';

export interface PromptSettings {
  selectedTemplate: string;
  customTemplate: PromptTemplate | null;
  rankingKeyword: string;
  additionalInstructions: string;
  [key: string]: any; // Make compatible with GlobalConfigValue
}

/**
 * Get current prompt settings from global config
 */
export const getPromptSettings = (): PromptSettings => {
  const stored = globalConfig.get('promptSettings') as Partial<PromptSettings> | undefined;
  
  return {
    selectedTemplate: stored?.selectedTemplate || DEFAULT_PROMPT_SETTINGS.selectedTemplate,
    customTemplate: stored?.customTemplate || DEFAULT_PROMPT_SETTINGS.customTemplate,
    rankingKeyword: stored?.rankingKeyword || DEFAULT_PROMPT_SETTINGS.rankingKeyword,
    additionalInstructions: stored?.additionalInstructions || DEFAULT_PROMPT_SETTINGS.additionalInstructions
  };
};

/**
 * Save prompt settings to global config
 */
export const savePromptSettings = async (settings: PromptSettings): Promise<void> => {
  await globalConfig.setAsync('promptSettings', settings);
};

/**
 * Get the active prompt template (either selected template or custom)
 */
export const getActiveTemplate = (): PromptTemplate => {
  const settings = getPromptSettings();
  
  // If using custom template, return it
  if (settings.customTemplate) {
    return settings.customTemplate;
  }
  
  // Otherwise get the selected template
  return getTemplate(settings.selectedTemplate);
};

/**
 * Reset prompt settings to defaults
 */
export const resetPromptSettings = async (): Promise<void> => {
  await savePromptSettings({
    selectedTemplate: ACADEMIC_TEMPLATE.id,
    customTemplate: null,
    rankingKeyword: ACADEMIC_TEMPLATE.rankingKeyword,
    additionalInstructions: ''
  });
}; 