// This isn't very secure, but given only BlueDot Impact employees should have access to the extension and we have a limit on the usage this is fine for now. 
export const anthropicApiKey = "***REMOVED***";
// OpenAI model to use, in the format accepted by the OpenAI API: https://platform.openai.com/docs/models/model-endpoint-compatibility
export const anthropicModel = 'claude-3-sonnet-20240229';
// Maximum number of open requests to OpenAI at any one time. Higher = faster, but more likely to hit OpenAI rate limits.
export const anthropicRequestConcurrency = 30;
