import { env } from '../../env';

export const openAiApiKey = env.OPENAI_API_KEY;
export const openAiOrganisation = 'CONFIGURE_ORGANISATION_HERE';
// Model to use: https://platform.openai.com/docs/models/model-endpoint-compatibility
export const openAiModel = 'CONFIGURE_MODEL_HERE';
// Maximum number of open requests at any one time. Higher = faster, but more likely to hit rate limits. From trial and error, at tier 3 with GPT-4 turbo, 30 works well.
export const openAiRequestConcurrency = 30;
