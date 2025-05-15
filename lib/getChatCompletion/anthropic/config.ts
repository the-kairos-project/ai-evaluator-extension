import { env } from '../../env';

export const anthropicApiKey = env.ANTHROPIC_API_KEY;
// Model to use: https://docs.anthropic.com/en/docs/models-overview
export const anthropicModel = 'CONFIGURE_MODEL_HERE';
// Maximum number of open requests at any one time. Higher = faster, but more likely to hit rate limits.
export const anthropicRequestConcurrency = 30;
