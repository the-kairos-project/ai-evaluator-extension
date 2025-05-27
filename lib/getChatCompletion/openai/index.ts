import pLimit from 'p-limit';
import type { GetChatCompletion } from '..';
import { getCurrentConcurrency } from '../../concurrency/config';
import { openAiApiKey, openAiModel, openAiOrganisation } from './config';

// Create rate limiter with dynamic concurrency
let globalRateLimit = pLimit(getCurrentConcurrency());
let lastConcurrency = getCurrentConcurrency();

// Function to update rate limiter if concurrency changed
const updateRateLimit = () => {
  const currentConcurrency = getCurrentConcurrency();
  if (currentConcurrency !== lastConcurrency) {
    globalRateLimit = pLimit(currentConcurrency);
    lastConcurrency = currentConcurrency;
    console.log(
      `🔄 Updated OpenAI rate limit to ${currentConcurrency} concurrent calls`
    );
  }
  return globalRateLimit;
};

export const getChatCompletion: GetChatCompletion = async (messages) => {
  return updateRateLimit()(async () => {
    try {
      const apiUrl = 'https://api.openai.com/v1/chat/completions';
      console.log(`🌐 DIRECT OpenAI API call to: ${apiUrl} (no proxy)`);

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${openAiApiKey}`,
          'OpenAI-Organization': openAiOrganisation,
        },
        body: JSON.stringify({
          model: openAiModel,
          messages: messages,
          max_tokens: 500,
        }),
      });

      if (!response.ok || response.status >= 400) {
        const errorText = await response.text();
        throw new Error(
          `HTTP error calling OpenAI API: got status ${response.status}. Response: ${errorText}`
        );
      }

      const data = await response.json();
      return data.choices[0].message.content;
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        throw new Error(
          'Network error: Unable to reach OpenAI API. Check your internet connection.'
        );
      }
      throw error;
    }
  });
};
