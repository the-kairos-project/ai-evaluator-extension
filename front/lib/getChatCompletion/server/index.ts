import { globalConfig } from '@airtable/blocks';
import { GetChatCompletion } from '..';
import { getAnthropicApiKey, getAnthropicModelName, getOpenAiApiKey, getOpenAiModelName, getSelectedModelProvider } from '../apiKeyManager';
import { getChatCompletionForProvider } from '..';
import pRetry from 'p-retry';
import { Logger } from '../../logger';

// Defaults (can be overridden via globalConfig)
const DEFAULT_MAX_RETRIES = 2;
const DEFAULT_REQUEST_TIMEOUT = 1800000; // 30 minutes default to accommodate enrichment calls

// In-memory flag to ensure we prompt the user at most once per batch/session
let hasShownServerFallbackPrompt = false;

function getRequestTimeout(): number {
  const cfg = globalConfig.get('serverRequestTimeout');
  if (typeof cfg === 'number' && !isNaN(cfg)) return cfg;
  if (typeof cfg === 'string' && !isNaN(Number(cfg))) return Number(cfg);
  return DEFAULT_REQUEST_TIMEOUT;
}

function getServerMaxRetries(): number {
  const cfg = globalConfig.get('serverMaxRetries');
  if (typeof cfg === 'number' && !isNaN(cfg)) return cfg;
  if (typeof cfg === 'string' && !isNaN(Number(cfg))) return Number(cfg);
  return DEFAULT_MAX_RETRIES;
}

export function resetServerFallbackPrompt(): void {
  hasShownServerFallbackPrompt = false;
}

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
  // Add a 5-minute buffer to avoid using a token that's close to expiring
  const currentTime = Date.now();
  const isValid = tokenCache.expiresAt > currentTime + 5 * 60 * 1000;
  if (!isValid) {
    Logger.info('Auth token nearing expiry; refreshing');
  }
  return isValid;
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
    Logger.error('Error parsing JWT token:', error);
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
    Logger.debug('Using cached authentication token');
    return tokenCache.token;
  }
  
  Logger.info('Getting new authentication token');
  const { username, password } = getServerCredentials();
  const serverUrl = getServerUrl();
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), getRequestTimeout());
    
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
      Logger.info(`Token cached, expires at ${new Date(tokenCache.expiresAt).toLocaleTimeString()}`);
    } else {
      // If we can't parse the token, still cache it but with the expires_in from the response
      tokenCache = {
        token,
        expiresAt: Date.now() + (data.expires_in * 1000), // Convert seconds to milliseconds
      };
      Logger.info(`Token cached with fallback expiration, expires at ${new Date(tokenCache.expiresAt).toLocaleTimeString()}`);
    }
    
    return token;
  } catch (error) {
    Logger.error('Error authenticating with server:', error);
    
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
  Logger.info('Token cache cleared');
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
  Logger.info(`🌐 SERVER-ROUTED ${selectedProvider.toUpperCase()} API call via: ${serverUrl}/api/v1/llm/${selectedProvider}`);

  try {
    // Use p-retry for automatic retries
    return await pRetry(async () => {
      try {
        // Get a token (cached if available)
        const token = await getAuthToken();
        
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), getRequestTimeout());
        
        Logger.debug(`📤 Sending request to server: ${serverUrl}/api/v1/llm/${selectedProvider}`);
        
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
            Logger.warn('🔄 Received 401 Unauthorized, clearing token cache and retrying');
            clearTokenCache();
            throw new Error('Authentication token expired or invalid');
          }
          
          const errorText = await response.text();
          Logger.error(`🚫 Server error: ${response.status} ${response.statusText}. ${errorText}`);
          throw new Error(`Server returned error: ${response.status} ${response.statusText}. ${errorText}`);
        }

        Logger.info('✅ Server response received successfully');
        const data = await response.json();
        
        // Extract the content from the response based on the provider
        if (selectedProvider === 'openai') {
          return data.choices[0].message.content;
        } else {
          return data.content[0].text;
        }
      } catch (error) {
        if (error.name === 'AbortError') {
          Logger.error('⏱️ Server request timed out');
          throw new Error('Server request timed out');
        }
        throw error;
      }
    }, {
      retries: getServerMaxRetries(),
      onFailedAttempt: (error) => {
        Logger.warn(`🔄 Attempt failed: ${error.message}. Retrying... (${error.attemptNumber}/${DEFAULT_MAX_RETRIES + 1})`);
      }
    });
  } catch (error) {
    Logger.error(`❌ Error calling ${selectedProvider} API via server:`, error);
    
    // Show error popup with fallback option at most once (per batch)
    if (!hasShownServerFallbackPrompt) {
      hasShownServerFallbackPrompt = true;
      if (confirm(`Server connection failed: ${error.message}\n\nWould you like to switch to direct API mode?`)) {
        Logger.info('🔄 Switching to direct API mode');
        await setServerMode(false);
        
        // Fallback to direct API call
        Logger.warn(`⚠️ Falling back to direct ${selectedProvider.toUpperCase()} API call`);
        return getChatCompletionForProvider(selectedProvider)(messages);
      }
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
  linkedinUrl?: string, // Optional LinkedIn URL parameter
  pdfResumeUrl?: string, // Optional PDF resume URL parameter
  useMultiAxis: boolean = false // Optional flag for multi-axis evaluation
): Promise<{ result: string; score: number | null; scores?: Array<{ name: string, score: number | null }> }> {
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
  Logger.info(`🌐 SERVER-ROUTED EVALUATION via: ${serverUrl}/api/v1/llm/evaluate`);
  Logger.debug(
    `📋 Evaluation details: Provider=${selectedProvider}, Model=${model}, Mode=${useMultiAxis ? 'multi-axis' : 'single-axis(SPAR-first-axis)'}
    `
  );
  
  // Log if LinkedIn enrichment is enabled
  if (linkedinUrl) {
    Logger.debug(`🔍 LinkedIn enrichment enabled with URL: ${linkedinUrl}`);
    Logger.debug(`🔍 LinkedIn URL format check: ${linkedinUrl.includes('linkedin.com') ? 'Valid LinkedIn domain' : 'Missing linkedin.com domain'}`);
    Logger.debug(`🔍 LinkedIn URL structure: ${linkedinUrl.includes('/in/') ? 'Contains /in/ path' : 'Missing /in/ path'}`);
  }
  
          // Log if PDF resume enrichment is enabled
  if (pdfResumeUrl) {
    Logger.debug(`📄 PDF resume enrichment enabled with URL: ${pdfResumeUrl}`);
  }

  try {
    // Use p-retry for automatic retries
    return await pRetry(async () => {
      try {
        // Get a token (cached if available)
        const token = await getAuthToken();
        
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), getRequestTimeout());
        
        Logger.debug(`📤 Sending evaluation request to server: ${serverUrl}/api/v1/llm/evaluate`);
        
        // Determine which URLs to use for enrichment
        let usePlugin = false;
        let sourceUrl: string | undefined = undefined;
        let pdfUrl: string | undefined = undefined;
        
        // Set up plugin usage and URLs
        if (linkedinUrl) {
          usePlugin = true;
          sourceUrl = linkedinUrl;
        }
        
        if (pdfResumeUrl) {
          usePlugin = true;
          // If we already have LinkedIn URL, set PDF as separate parameter
          if (linkedinUrl) {
            pdfUrl = pdfResumeUrl;
          } else {
            // Otherwise use it as the main source URL
            sourceUrl = pdfResumeUrl;
          }
        }
        
        // Create request payload (send only what the server actually needs)
        const requestPayload: Record<string, unknown> = {
          api_key: apiKey,
          provider: selectedProvider,
          model: model,
          applicant_data: applicantData,
          criteria_string: criteriaString,
        };

        // Multi-axis flag (server defaults behavior if omitted)
        if (useMultiAxis) {
          requestPayload.use_multi_axis = true;
        }

        // Plugin payload only when enrichment is requested
        if (usePlugin) {
          requestPayload.use_plugin = true;
          if (sourceUrl) requestPayload.source_url = sourceUrl;
          if (pdfUrl) requestPayload.pdf_url = pdfUrl;
        }

        // Only include template fields when explicitly needed in future; for now, omit
        // single-axis defaults to SPAR-first-axis on the server, multi-axis uses SPAR too
        
        // Log the request payload for debugging (excluding API key)
        Logger.debug(
          `📦 Request payload: ${JSON.stringify(
            { ...requestPayload, api_key: '[REDACTED]' },
            null,
            2
          )}`
        );
        
        // Make the request to the server's evaluate endpoint
        const response = await fetch(`${serverUrl}/api/v1/llm/evaluate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(requestPayload),
          signal: controller.signal,
        });
        
        // Clear timeout
        clearTimeout(timeoutId);

        if (!response.ok) {
          // If unauthorized, clear token cache and retry
          if (response.status === 401) {
            Logger.warn('🔄 Received 401 Unauthorized, clearing token cache and retrying');
            clearTokenCache();
            throw new Error('Authentication token expired or invalid');
          }
          
          const errorText = await response.text();
          Logger.error(`🚫 Server evaluation error: ${response.status} ${response.statusText}. ${errorText}`);
          throw new Error(`Server returned error: ${response.status} ${response.statusText}. ${errorText}`);
        }

        Logger.info('✅ Server evaluation response received successfully');
        const data = await response.json();
        Logger.info(`📊 Evaluation result: Score=${data.score !== null ? data.score : 'NULL'}`);
        
        // Log multi-axis scores if present
        if (data.scores && Array.isArray(data.scores)) {
          Logger.info('📊 Multi-axis evaluation scores:');
          data.scores.forEach(axisScore => {
            Logger.info(`  - ${axisScore.name}: ${axisScore.score !== null ? axisScore.score : 'NULL'}`);
          });
        }
        
        // Extract LinkedIn data if present
        const linkedinDataMatch = data.result.match(/\[LINKEDIN_DATA\]([\s\S]*?)\[END_LINKEDIN_DATA\]/);
        if (linkedinDataMatch && linkedinDataMatch[1]) {
          Logger.info('📋 LinkedIn data found in response:');
          try {
            const linkedinData = JSON.parse(linkedinDataMatch[1]);
            Logger.debug('🔍 LinkedIn profile data:', linkedinData);
          } catch (e) {
            Logger.debug('📝 LinkedIn data (raw):', linkedinDataMatch[1]);
          }
        } else {
          Logger.warn('⚠️ No LinkedIn data found in response');
        }
        
        // Extract PDF resume data if present
        const pdfResumeDataMatch = data.result.match(/\[PDF_RESUME_DATA\]([\s\S]*?)\[END_PDF_RESUME_DATA\]/);
        if (pdfResumeDataMatch && pdfResumeDataMatch[1]) {
          Logger.info('📄 PDF resume data found in response:');
          try {
            const pdfResumeData = JSON.parse(pdfResumeDataMatch[1]);
            Logger.debug('🔍 PDF resume data:', pdfResumeData);
          } catch (e) {
            Logger.debug('📝 PDF resume data (raw):', pdfResumeDataMatch[1]);
          }
        } else {
          Logger.warn('⚠️ No PDF resume data found in response');
        }
        
        // Extract enrichment logs if present
        const enrichmentLogMatch = data.result.match(/\[ENRICHMENT LOG\]([\s\S]*?)\[END ENRICHMENT LOG\]/);
        if (enrichmentLogMatch && enrichmentLogMatch[1]) {
          Logger.info('📋 Enrichment logs:');
          Logger.debug(enrichmentLogMatch[1]);
        } else {
          Logger.warn('⚠️ No enrichment logs found in response');
        }
        
        return {
          result: data.result,
          score: data.score,
          scores: data.scores
        };
      } catch (error) {
        if (error.name === 'AbortError') {
          Logger.error('⏱️ Server evaluation request timed out');
          throw new Error('Server request timed out');
        }
        throw error;
      }
    }, {
      retries: getServerMaxRetries(),
      onFailedAttempt: (error) => {
        Logger.warn(`🔄 Evaluation attempt failed: ${error.message}. Retrying... (${error.attemptNumber}/${DEFAULT_MAX_RETRIES + 1})`);
      }
    });
  } catch (error) {
    Logger.error(`❌ Error calling evaluation API via server:`, error);
    
    // Show error popup with fallback option at most once (per batch)
    if (!hasShownServerFallbackPrompt) {
      hasShownServerFallbackPrompt = true;
      if (confirm(`Server evaluation failed: ${error.message}\n\nWould you like to switch to direct API mode?`)) {
        Logger.info('🔄 Switching to direct API mode');
        await setServerMode(false);
        
        // Return null to indicate fallback needed (handled by caller)
        Logger.warn(`⚠️ Returning null score to trigger fallback to direct mode`);
        return { result: '', score: null };
      }
    }

    throw error;
  }
} 