import { env } from "../../env";

export const anthropicApiKey = env.ANTHROPIC_API_KEY;
// Model to use: https://docs.anthropic.com/en/docs/models-overview
export const anthropicModel = "claude-3-5-sonnet-20241022";
// Maximum number of open requests at any one time. Higher = faster, but more likely to hit rate limits.
export const anthropicRequestConcurrency = 30;
