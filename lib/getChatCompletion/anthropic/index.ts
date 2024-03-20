import pLimit from 'p-limit';
import { anthropicRequestConcurrency, anthropicApiKey, anthropicModel } from './config';
import { GetChatCompletion } from '..';

const globalRateLimit = pLimit(anthropicRequestConcurrency);

const supportedRoles = ['user', 'assistant']

export const getChatCompletion: GetChatCompletion = async (messages) => {
  const transformedMessages = messages.map(m => ({ ...m, role: supportedRoles.includes(m.role) ? m.role : 'user' }));

  return globalRateLimit(async () => {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': anthropicApiKey,
          'OpenAI-Organization': 'org-2egSVUATOaBoS2Slr2CbYrcZ',
        },
        body: JSON.stringify({
          model: anthropicModel,
          messages: transformedMessages,
          max_tokens: 500,
        })
    });
    
    if (!response.ok || response.status >= 400) {
        throw new Error(`HTTP error calling API: got status ${response.status}`);
    }

    const data = await response.json();
    return data.content[0].text;
  });
}