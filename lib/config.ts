// This isn't very secure, but given only BlueDot Impact employees should have access to the extension and we have a limit on the usage this is fine for now. 
export const openAiApiKey = "***REMOVED***";
// OpenAI model to use, in the format accepted by the OpenAI API: https://platform.openai.com/docs/models/model-endpoint-compatibility
export const openAiModel = 'gpt-3.5-turbo';
// Maximum number of open requests to OpenAI at any one time. Higher = faster, but more likely to hit OpenAI rate limits. From trial and error, between 1 and 3 seems about right.
export const openAiRequestConcurrency = 2;
