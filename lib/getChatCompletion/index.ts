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
  
  const startTime = Date.now();
  const tokenCount = messages.reduce((sum, msg) => sum + msg.content.length, 0);
  
  const modelName = selectedProvider === 'openai' 
    ? (await import('./apiKeyManager')).getOpenAiModelName()
    : (await import('./apiKeyManager')).getAnthropicModelName();
  
  console.log(`🚀 API Call to ${selectedProvider} using ${modelName} (approx ${Math.round(tokenCount / 4)} tokens)`);
  
  try {
    const result = await completionFunction(messages);
    const duration = Date.now() - startTime;
    console.log(`🎉 API Response from ${selectedProvider} in ${duration}ms (${result.length} chars)`);
    return result;
  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`💥 API Error from ${selectedProvider} after ${duration}ms:`, error);
    throw error;
  }
};
