// This isn't very secure, but given only BlueDot Impact employees should have access to the extension and we have a limit on the usage this is fine for now. 
export const openAiApiKey = "***REMOVED***";
// OpenAI model to use, in the format accepted by the OpenAI API: https://platform.openai.com/docs/models/model-endpoint-compatibility
export const openAiModel = 'gpt-4-1106-preview';
// Maximum number of open requests to OpenAI at any one time. Higher = faster, but more likely to hit OpenAI rate limits. From trial and error, at tier 3 with GPT-4 turbo, 30 works well.
export const openAiRequestConcurrency = 30;
