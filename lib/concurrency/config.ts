/**
 * Concurrency configuration for API calls
 * Controls how many simultaneous API requests are made
 */

import { globalConfig } from '@airtable/blocks';

// Default concurrency values - current hardcoded values
export const DEFAULT_CONCURRENCY = 5;

// Available concurrency options with descriptions
export const CONCURRENCY_OPTIONS = [
  {
    label: 'Minimal (5 calls)',
    value: 5,
    description: 'Very conservative, lowest chance of rate limits'
  },
  {
    label: 'Conservative (10 calls)',
    value: 10,
    description: 'Safe and stable, good for testing'
  },
  {
    label: 'Balanced (20 calls)', 
    value: 20,
    description: 'Good balance of speed and stability (default)'
  },
  {
    label: 'Aggressive (30 calls)',
    value: 30,
    description: 'Faster but may hit rate limits on some plans'
  }
];

/**
 * Get the currently configured concurrency setting
 */
export const getCurrentConcurrency = (): number => {
  const stored = globalConfig.get('apiConcurrency') as number;
  return stored || DEFAULT_CONCURRENCY;
};

/**
 * Save concurrency setting to global config
 */
export const saveConcurrency = async (concurrency: number): Promise<void> => {
  await globalConfig.setAsync('apiConcurrency', concurrency);
};

/**
 * Get concurrency option details for display
 */
export const getConcurrencyOption = (value: number) => {
  return CONCURRENCY_OPTIONS.find(option => option.value === value) || {
    label: `Custom (${value} calls)`,
    value,
    description: 'Custom concurrency setting'
  };
}; 