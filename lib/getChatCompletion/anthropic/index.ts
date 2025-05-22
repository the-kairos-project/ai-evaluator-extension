import pLimit from 'p-limit';
import { anthropicRequestConcurrency, anthropicApiKey, anthropicModel } from './config';
import type { GetChatCompletion } from '..';

const globalRateLimit = pLimit(anthropicRequestConcurrency);

export const getChatCompletion: GetChatCompletion = async (messages) => {
  const lastMessageIsSystem = messages[messages.length - 1]?.role === 'system';

  return globalRateLimit(async () => {
    try {
      const proxyUrl = 'http://localhost:8010/proxy/v1/messages';
      console.log(`🔄 PROXIED Anthropic API call to: ${proxyUrl} (via proxy -> https://api.anthropic.com)`);
      
      const response = await fetch(proxyUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'anthropic-version': '2023-06-01',
          'x-api-key': anthropicApiKey,
        },
        body: JSON.stringify({
          model: anthropicModel,
          messages: lastMessageIsSystem ? messages.slice(0, -1) : messages,
          system: lastMessageIsSystem ? messages[messages.length - 1].content : undefined,
          max_tokens: 500,
        }),
      });

      if (!response.ok || response.status >= 400) {
        const errorText = await response.text();
        throw new Error(`HTTP error calling API: got status ${response.status}. Response: ${errorText}`);
      }

      const data = await response.json();
      return data.content[0].text;
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        throw new Error('Proxy server not running. Please start it with: bun run proxy.ts');
      }
      throw error;
    }
  });
};
