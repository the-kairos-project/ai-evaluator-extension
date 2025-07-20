import { globalConfig } from '@airtable/blocks';
import { GetChatCompletion } from '..';
import { getAnthropicApiKey, getAnthropicModelName, getOpenAiApiKey, getOpenAiModelName, getSelectedModelProvider } from '../apiKeyManager';
import { getChatCompletionForProvider } from '..';
import pRetry from 'p-retry';

// Maximum number of retries for server connection
const MAX_RETRIES = 2;

// Timeout for server requests in milliseconds
const REQUEST_TIMEOUT = 100000;

// Cache for auth token
interface TokenCache {
  token: string;
  expiresAt: number; // Timestamp when token expires
}

// In-memory token cache
let tokenCache: TokenCache | null = null;

/**
 * Gets the server URL from global config
 */
export function getServerUrl(): string {
  return (globalConfig.get('serverUrl') as string) || 'http://localhost:8000';
}

/**
 * Gets the server credentials from global config
 */
export function getServerCredentials(): { username: string; password: string } {
  return {
    username: (globalConfig.get('serverUsername') as string) || 'admin',
    password: (globalConfig.get('serverPassword') as string) || 'admin123',
  };
}

/**
 * Checks if server mode is enabled
 */
export function isServerModeEnabled(): boolean {
  return (globalConfig.get('useServerMode') as boolean) || false;
}

/**
 * Sets server mode in global config
 */
export async function setServerMode(enabled: boolean): Promise<void> {
  await globalConfig.setAsync('useServerMode', enabled);
}

/**
 * Checks if the cached token is still valid
 */
function isTokenValid(): boolean {
  if (!tokenCache) return false;
  
  // Add a 30-second buffer to ensure we don't use a token that's about to expire
  const currentTime = Date.now();
  return tokenCache.expiresAt > currentTime + 30000;
}

/**
 * Parses JWT token to get expiration time
 */
function parseJwt(token: string): { exp: number } | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));

    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Error parsing JWT token:', error);
    return null;
  }
}

/**
 * Gets an authentication token from the server
 * Uses cached token if available and not expired
 */
async function getAuthToken(): Promise<string> {
  // If we have a valid cached token, use it
  if (isTokenValid() && tokenCache) {
    console.log('Using cached authentication token');
    return tokenCache.token;
  }
  
  console.log('Getting new authentication token');
  const { username, password } = getServerCredentials();
  const serverUrl = getServerUrl();
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    
    const response = await fetch(`${serverUrl}/api/v1/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        username,
        password,
      }),
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Authentication failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    const token = data.access_token;
    
    // Parse the JWT to get the expiration time
    const parsedToken = parseJwt(token);
    if (parsedToken && parsedToken.exp) {
      // Store the token with its expiration time
      tokenCache = {
        token,
        expiresAt: parsedToken.exp * 1000, // Convert to milliseconds
      };
      console.log(`Token cached, expires at ${new Date(tokenCache.expiresAt).toLocaleTimeString()}`);
    } else {
      // If we can't parse the token, still cache it but with the expires_in from the response
      tokenCache = {
        token,
        expiresAt: Date.now() + (data.expires_in * 1000), // Convert seconds to milliseconds
      };
      console.log(`Token cached with fallback expiration, expires at ${new Date(tokenCache.expiresAt).toLocaleTimeString()}`);
    }
    
    return token;
  } catch (error) {
    console.error('Error authenticating with server:', error);
    
    // Clear token cache on authentication error
    tokenCache = null;
    
    if (error.name === 'AbortError') {
      throw new Error('Server connection timed out. Please check your server URL or network connection.');
    }
    
    throw new Error('Failed to authenticate with server. Please check your server credentials.');
  }
}

/**
 * Clears the token cache
 * Useful when changing server settings or when a token is rejected
 */
export function clearTokenCache(): void {
  tokenCache = null;
  console.log('Token cache cleared');
}

/**
 * Gets a chat completion from the server
 */
export const getChatCompletion: GetChatCompletion = async (messages) => {
  const selectedProvider = getSelectedModelProvider();
  const serverUrl = getServerUrl();
  
  // Get the API key and model based on the selected provider
  const apiKey = selectedProvider === 'openai' 
    ? getOpenAiApiKey() 
    : getAnthropicApiKey();
  
  const model = selectedProvider === 'openai'
    ? getOpenAiModelName()
    : getAnthropicModelName();

  // Log the request
  console.log(`🌐 SERVER-ROUTED ${selectedProvider.toUpperCase()} API call via: ${serverUrl}/api/v1/llm/${selectedProvider}`);

  try {
    // Use p-retry for automatic retries
    return await pRetry(async () => {
      try {
        // Get a token (cached if available)
        const token = await getAuthToken();
        
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
        
        console.log(`📤 Sending request to server: ${serverUrl}/api/v1/llm/${selectedProvider}`);
        
        // Make the request to the server
        const response = await fetch(`${serverUrl}/api/v1/llm/${selectedProvider}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            api_key: apiKey,
            model: model,
            messages: messages,
          }),
          signal: controller.signal,
        });
        
        // Clear timeout
        clearTimeout(timeoutId);

        if (!response.ok) {
          // If unauthorized, clear token cache and retry
          if (response.status === 401) {
            console.log('🔄 Received 401 Unauthorized, clearing token cache and retrying');
            clearTokenCache();
            throw new Error('Authentication token expired or invalid');
          }
          
          const errorText = await response.text();
          console.error(`🚫 Server error: ${response.status} ${response.statusText}. ${errorText}`);
          throw new Error(`Server returned error: ${response.status} ${response.statusText}. ${errorText}`);
        }

        console.log('✅ Server response received successfully');
        const data = await response.json();
        
        // Extract the content from the response based on the provider
        if (selectedProvider === 'openai') {
          return data.choices[0].message.content;
        } else {
          return data.content[0].text;
        }
      } catch (error) {
        if (error.name === 'AbortError') {
          console.error('⏱️ Server request timed out');
          throw new Error('Server request timed out');
        }
        throw error;
      }
    }, {
      retries: MAX_RETRIES,
      onFailedAttempt: (error) => {
        console.warn(`🔄 Attempt failed: ${error.message}. Retrying... (${error.attemptNumber}/${MAX_RETRIES + 1})`);
      }
    });
  } catch (error) {
    console.error(`❌ Error calling ${selectedProvider} API via server:`, error);
    
    // Show error popup with fallback option
    if (confirm(`Server connection failed: ${error.message}\n\nWould you like to switch to direct API mode?`)) {
      console.log('🔄 Switching to direct API mode');
      await setServerMode(false);
      
      // Fallback to direct API call
      console.log(`⚠️ Falling back to direct ${selectedProvider.toUpperCase()} API call`);
      return getChatCompletionForProvider(selectedProvider)(messages);
    }
    
    throw error;
  }
};

/**
 * Evaluates an applicant using the server's evaluate endpoint
 */
export async function evaluateApplicantWithServer(
  applicantData: string,
  criteriaString: string,
  templateId: string = 'academic',
  rankingKeyword: string = 'FINAL_RANKING',
  additionalInstructions: string = ''
): Promise<{ result: string; score: number | null }> {
  const selectedProvider = getSelectedModelProvider();
  const serverUrl = getServerUrl();
  
  // Get the API key and model based on the selected provider
  const apiKey = selectedProvider === 'openai' 
    ? getOpenAiApiKey() 
    : getAnthropicApiKey();
  
  const model = selectedProvider === 'openai'
    ? getOpenAiModelName()
    : getAnthropicModelName();

  // Log the request
  console.log(`🌐 SERVER-ROUTED EVALUATION via: ${serverUrl}/api/v1/llm/evaluate`);
  console.log(`📋 Evaluation details: Provider=${selectedProvider}, Model=${model}, Template=${templateId}`);

  try {
    // Use p-retry for automatic retries
    return await pRetry(async () => {
      try {
        // Get a token (cached if available)
        const token = await getAuthToken();
        
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
        
        console.log(`📤 Sending evaluation request to server: ${serverUrl}/api/v1/llm/evaluate`);
        
        // Make the request to the server's evaluate endpoint
        const response = await fetch(`${serverUrl}/api/v1/llm/evaluate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            api_key: apiKey,
            provider: selectedProvider,
            model: model,
            applicant_data: applicantData,
            criteria_string: criteriaString,
            template_id: templateId,
            ranking_keyword: rankingKeyword,
            additional_instructions: additionalInstructions,
          }),
          signal: controller.signal,
        });
        
        // Clear timeout
        clearTimeout(timeoutId);

        if (!response.ok) {
          // If unauthorized, clear token cache and retry
          if (response.status === 401) {
            console.log('🔄 Received 401 Unauthorized, clearing token cache and retrying');
            clearTokenCache();
            throw new Error('Authentication token expired or invalid');
          }
          
          const errorText = await response.text();
          console.error(`🚫 Server evaluation error: ${response.status} ${response.statusText}. ${errorText}`);
          throw new Error(`Server returned error: ${response.status} ${response.statusText}. ${errorText}`);
        }

        console.log('✅ Server evaluation response received successfully');
        const data = await response.json();
        console.log(`📊 Evaluation result: Score=${data.score !== null ? data.score : 'NULL'}`);
        
        return {
          result: data.result,
          score: data.score
        };
      } catch (error) {
        if (error.name === 'AbortError') {
          console.error('⏱️ Server evaluation request timed out');
          throw new Error('Server request timed out');
        }
        throw error;
      }
    }, {
      retries: MAX_RETRIES,
      onFailedAttempt: (error) => {
        console.warn(`🔄 Evaluation attempt failed: ${error.message}. Retrying... (${error.attemptNumber}/${MAX_RETRIES + 1})`);
      }
    });
  } catch (error) {
    console.error(`❌ Error calling evaluation API via server:`, error);
    
    // Show error popup with fallback option
    if (confirm(`Server evaluation failed: ${error.message}\n\nWould you like to switch to direct API mode?`)) {
      console.log('🔄 Switching to direct API mode');
      await setServerMode(false);
      
      // Return null to indicate fallback needed (handled by caller)
      console.log(`⚠️ Returning null score to trigger fallback to direct mode`);
      return { result: '', score: null };
    }
    
    throw error;
  }
} 