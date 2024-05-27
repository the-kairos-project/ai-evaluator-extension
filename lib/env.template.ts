// For local development, you should usually edit env.ts (and not env.template.ts)
// env.template.ts is a template to set up semi-valid env variables for new projects

// This is very jank
// We're building secrets in to the source code accessible in the browser. This is because Airtable extensions don't have any sensible secret management mechanism.
// We're currently accepting this risk given:
// - only BlueDot Impact employees have access to the deployed extension
// - we have limits on API usage set for both platforms
// - the risk is people using our API credits / getting free access to APIs, which is not as critical (as e.g. applicant's personal data)
export const env = {
    // Get from https://platform.openai.com/settings/profile?tab=api-keys
    'OPENAI_API_KEY': 'sk-...',
    // Get from https://console.anthropic.com/settings/keys
    'ANTHROPIC_API_KEY': 'sk-ant-api...'
}
