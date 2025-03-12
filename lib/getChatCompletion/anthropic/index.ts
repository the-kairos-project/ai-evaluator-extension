import pLimit from 'p-limit';
import { anthropicRequestConcurrency, anthropicApiKey, anthropicModel } from './config';
import { GetChatCompletion } from '..';

const globalRateLimit = pLimit(anthropicRequestConcurrency);

export const getChatCompletion: GetChatCompletion = async (messages) => {
  const lastMessageIsSystem = messages[messages.length - 1]?.role === 'system';

  return globalRateLimit(async () => {
    const response = await fetch('http://localhost:8010/proxy/v1/messages', {
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
      throw new Error(`HTTP error calling API: got status ${response.status}`);
    }

    const data = await response.json();
    return data.content[0].text;
  });
};
