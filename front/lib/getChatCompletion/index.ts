import type { ModelProvider } from '../models/config';
import { getChatCompletion as anthropicGetChatCompletion } from './anthropic';
import { getSelectedModelProvider } from './apiKeyManager';
import { getChatCompletion as openAiGetChatCompletion } from './openai';
import { getChatCompletion as serverGetChatCompletion, isServerModeEnabled } from './server';

export type Prompt = {
  role: 'system' | 'user' | 'assistant' | 'function';
  content: string;
}[];
export type GetChatCompletion = (messages: Prompt) => Promise<string>;

/**
 * Gets the appropriate chat completion function for the given provider
 */
export function getChatCompletionForProvider(
  provider: ModelProvider
): GetChatCompletion {
  switch (provider) {
    case 'openai':
      return openAiGetChatCompletion;
    case 'anthropic':
      return anthropicGetChatCompletion;
    default:
      throw new Error(`Unknown provider: ${provider}`);
  }
}

/**
 * Gets a chat completion from the user-selected model provider
 */
export const getChatCompletion: GetChatCompletion = async (messages) => {
  const selectedProvider = getSelectedModelProvider();
  
  // Check if server mode is enabled
  const useServerMode = isServerModeEnabled();
  
  // Add detailed logging about routing decision
  console.log(`🔍 ROUTING DECISION: Server Mode is ${useServerMode ? 'ENABLED' : 'DISABLED'}`);
  
  // Use server-routed or direct API call based on setting
  const completionFunction = useServerMode 
    ? serverGetChatCompletion
    : getChatCompletionForProvider(selectedProvider);

  // Log which function will be used
  console.log(`🔀 Using ${useServerMode ? 'SERVER-ROUTED' : 'DIRECT'} API call for ${selectedProvider}`);

  const startTime = Date.now();
  const tokenCount = messages.reduce((sum, msg) => sum + msg.content.length, 0);

  const modelName =
    selectedProvider === 'openai'
      ? (await import('./apiKeyManager')).getOpenAiModelName()
      : (await import('./apiKeyManager')).getAnthropicModelName();

  console.log(
    `🚀 API Call to ${selectedProvider} using ${modelName} (approx ${Math.round(tokenCount / 4)} tokens)`
  );

  try {
    const result = await completionFunction(messages);
    const duration = Date.now() - startTime;
    console.log(
      `🎉 API Response from ${selectedProvider} in ${duration}ms (${result.length} chars)`
    );
    return result;
  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`💥 API Error from ${selectedProvider} after ${duration}ms:`, error);
    throw error;
  }
};
