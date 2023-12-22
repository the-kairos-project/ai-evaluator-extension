import pLimit from 'p-limit';
import { openAiRequestConcurrency, openAiApiKey, openAiModel } from './config';

export type Prompt = { role: 'system' | 'user' | 'assistant' | 'function', content: string }[];

const globalRateLimit = pLimit(openAiRequestConcurrency);

export async function getChatCompletion(
  messages: Prompt,
): Promise<string> {
  return globalRateLimit(async () => {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${openAiApiKey}`,
          'OpenAI-Organization': 'org-2egSVUATOaBoS2Slr2CbYrcZ',
        },
        body: JSON.stringify({
          model: openAiModel,
          messages: messages,
          max_tokens: 500
        })
    });
    
    if (!response.ok || response.status >= 400) {
        throw new Error(`HTTP error calling API: got status ${response.status}`);
    }

    const data = await response.json();
    return data.choices[0].message.content;
  });
}