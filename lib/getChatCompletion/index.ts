import { getSelectedModelProvider } from './apiKeyManager';
import { ModelProvider } from '../models/config';
import { getChatCompletion as openAiGetChatCompletion } from './openai';
import { getChatCompletion as anthropicGetChatCompletion } from './anthropic';

export type Prompt = {
  role: 'system' | 'user' | 'assistant' | 'function';
  content: string;
}[];
export type GetChatCompletion = (messages: Prompt) => Promise<string>;

/**
 * Returns the appropriate chat completion function based on the selected model provider
 */
export const getChatCompletionForProvider = (provider: ModelProvider): GetChatCompletion => {
  switch (provider) {
    case 'openai':
      return openAiGetChatCompletion;
    case 'anthropic':
      return anthropicGetChatCompletion;
    default:
      return openAiGetChatCompletion;
  }
};

/**
 * Gets a chat completion from the user-selected model provider
 */
export const getChatCompletion: GetChatCompletion = async (messages) => {
  const selectedProvider = getSelectedModelProvider();
  const completionFunction = getChatCompletionForProvider(selectedProvider);
  return completionFunction(messages);
};
