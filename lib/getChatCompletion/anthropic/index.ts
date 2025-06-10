import pLimit from 'p-limit';
import type { GetChatCompletion } from '..';
import { getCurrentConcurrency } from '../../concurrency/config';
import { anthropicApiKey, anthropicModel } from './config';

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
      `🔄 Updated Anthropic rate limit to ${currentConcurrency} concurrent calls`
    );
  }
  return globalRateLimit;
};

export const getChatCompletion: GetChatCompletion = async (messages) => {
  const lastMessageIsSystem = messages[messages.length - 1]?.role === 'system';

  return updateRateLimit()(async () => {
    try {
      const apiUrl = 'https://api.anthropic.com/v1/messages';
      console.log(`🌐 DIRECT Anthropic API call to: ${apiUrl}`);

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'anthropic-version': '2023-06-01',
          'x-api-key': anthropicApiKey,
          'anthropic-dangerous-direct-browser-access': 'true',
        },
        body: JSON.stringify({
          model: anthropicModel,
          messages: lastMessageIsSystem ? messages.slice(0, -1) : messages,
          system: lastMessageIsSystem
            ? messages[messages.length - 1].content
            : undefined,
          max_tokens: 500,
        }),
      });

      // Read rate limit headers for potential future use
      const remainingRequests = response.headers.get(
        'anthropic-ratelimit-requests-remaining'
      );
      const remainingTokens = response.headers.get(
        'anthropic-ratelimit-tokens-remaining'
      );
      const resetTime = response.headers.get('anthropic-ratelimit-requests-reset');

      if (remainingRequests && Number.parseInt(remainingRequests) < 10) {
        console.warn(
          `🚨 Anthropic API: Only ${remainingRequests} requests remaining until ${resetTime}`
        );
      }

      if (remainingTokens && Number.parseInt(remainingTokens) < 1000) {
        console.warn(
          `🚨 Anthropic API: Only ${remainingTokens} tokens remaining until ${resetTime}`
        );
      }

      if (!response.ok || response.status >= 400) {
        const errorText = await response.text();
        throw new Error(
          `HTTP error calling API: got status ${response.status}. Response: ${errorText}`
        );
      }

      const data = await response.json();
      return data.content[0].text;
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        throw new Error(
          'Failed to connect to Anthropic API. Please check your internet connection and API key.'
        );
      }
      throw error;
    }
  });
};
