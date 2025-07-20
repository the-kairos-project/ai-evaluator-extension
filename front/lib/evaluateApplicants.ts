import type { Record as AirtableRecord, Table } from '@airtable/blocks/models';
import pRetry from 'p-retry';
import { getChatCompletion } from './getChatCompletion';
import { isServerModeEnabled, evaluateApplicantWithServer } from './getChatCompletion/server';
import type { Preset } from './preset';
import {
  buildPrompt,
  getActiveTemplate,
  getPromptSettings,
  getRankingKeyword,
} from './prompts';

export type SetProgress = (updater: (prev: number) => number) => void;

/**
 * @returns array of promises, each expected to return an evaluation
 */

// Cached field map to avoid repetitive lookups across multiple calls
const fieldNameCache = new Map<string, string>();

/**
 * Helper functions for simplified logging
 */
// Get a simple identifier for an applicant
const getApplicantIdentifier = (applicant: Record<string, string>): string => {
  // Try to find name or id field first
  const nameField = Object.entries(applicant).find(
    ([key, value]) =>
      (key.toLowerCase().includes('name') || key.toLowerCase().includes('id')) && value
  );

  if (nameField) {
    return nameField[1].substring(0, 30);
  }

  // If no name/id field, use the first non-empty field value as identifier
  const firstField = Object.entries(applicant).find(([, value]) => value?.trim());
  if (firstField) {
    return `${firstField[0]}: ${firstField[1].substring(0, 20)}...`;
  }

  return 'unknown';
};

/**
 * Extracts applicant name from record for display purposes
 * Tries primary field first, then any field containing "name", finally falls back to record ID
 */
const getApplicantName = (applicant: AirtableRecord): string => {
  try {
    // Try to get the primary field value (usually the name)
    const primaryField = (applicant as any).parentTable?.primaryField;
    if (primaryField) {
      const primaryValue = applicant.getCellValueAsString(primaryField.id);
      if (primaryValue?.trim()) {
        return primaryValue.trim();
      }
    }

    // Fallback: look for any field containing "name"
    const allFields = (applicant as any).parentTable?.fields || [];
    for (const field of allFields) {
      if (field.name.toLowerCase().includes('name')) {
        const value = applicant.getCellValueAsString(field.id);
        if (value?.trim()) {
          return value.trim();
        }
      }
    }
  } catch (error) {
    // Continue to final fallback
  }

  // Final fallback: use record ID
  return `Applicant ${applicant.id}`;
};

/**
 * Sets the applicant's name in the evaluation record's primary field
 * This ensures the evaluation record has a readable name for identification
 */
const setApplicantNameInResult = (
  result: Record<string, unknown>,
  applicant: AirtableRecord,
  evaluationTable?: Table
): void => {
  if (!evaluationTable?.primaryField) return;

  const applicantName = getApplicantName(applicant);
  result[evaluationTable.primaryField.id] = applicantName;
};

// Helper to get field names from the table
const getFieldNames = (
  applicant: AirtableRecord,
  preset: Preset
): Map<string, string> => {
  const fieldNameMap = new Map<string, string>();

  try {
    // Access parentTable from AirtableRecord
    const table = (applicant as any).parentTable;

    // Get all field names in a single batch for better performance
    for (const { fieldId } of preset.evaluationFields) {
      // Check if we already have this field name cached
      if (fieldNameCache.has(fieldId)) {
        fieldNameMap.set(fieldId, fieldNameCache.get(fieldId));
        continue;
      }

      try {
        const field = table.getFieldByIdIfExists(fieldId);
        if (field) {
          const fieldName = field.name;
          // Cache for future use
          fieldNameCache.set(fieldId, fieldName);
          fieldNameMap.set(fieldId, fieldName);
        }
      } catch (e) {
        // Silently continue - we'll use the ID if the name is not available
      }
    }
  } catch (e) {
    // Silent fail - will fall back to using IDs
  }

  return fieldNameMap;
};

// Helper to build dependency map from evaluation fields
const buildDependencyMap = (
  preset: Preset
): { dependencyMap: Map<string, string[]>; hasStandaloneFields: boolean } => {
  const dependencyMap = new Map<string, string[]>();

  // For each evaluation field that has a dependency, record that information
  for (const { fieldId, dependsOnInputField } of preset.evaluationFields) {
    if (dependsOnInputField) {
      // Store the mapping from input field to dependent output fields
      if (!dependencyMap.has(dependsOnInputField)) {
        dependencyMap.set(dependsOnInputField, []);
      }
      dependencyMap.get(dependsOnInputField).push(fieldId);
    }
  }

  // Check if any fields need to be evaluated at all
  const hasStandaloneFields = preset.evaluationFields.some(
    ({ dependsOnInputField }) => !dependsOnInputField
  );

  return { dependencyMap, hasStandaloneFields };
};

// Determine which fields to skip based on empty dependency fields
const determineSkipFields = (
  dependencyMap: Map<string, string[]>,
  plainRecord: Record<string, string>,
  preset: Preset
): Set<string> => {
  const skipFields = new Set<string>();

  dependencyMap.forEach((dependentFields, inputFieldId) => {
    // Get the value from the plain record
    const key =
      preset.applicantFields.find((f) => f.fieldId === inputFieldId)?.questionName ||
      inputFieldId;
    const value = plainRecord[key] || plainRecord[inputFieldId] || '';

    // If empty, mark all dependent fields to be skipped
    if (!value || value.trim() === '') {
      for (const fieldId of dependentFields) {
        skipFields.add(fieldId);
      }
    }
  });

  return skipFields;
};

export const evaluateApplicants = (
  applicants: AirtableRecord[],
  preset: Preset,
  setProgress: SetProgress,
  evaluationTable?: Table
): Promise<Record<string, unknown>>[] => {
  // Fast path: if empty, nothing to process
  if (!applicants.length || !preset.evaluationFields.length) {
    return [];
  }

  // Get field names for better error messages
  const fieldNameMap =
    applicants.length > 0
      ? getFieldNames(applicants[0], preset)
      : new Map<string, string>();

  // Log basic processing info
  console.log(
    `Processing ${applicants.length} applicants with ${preset.evaluationFields.length} evaluation fields`
  );

  // Build dependency map
  const { dependencyMap, hasStandaloneFields } = buildDependencyMap(preset);

  // Log dependency info
  if (dependencyMap.size > 0) {
    console.log(
      `Field dependencies: ${dependencyMap.size} input fields have dependent output fields`
    );
  }

  // Log setup info
  if (evaluationTable?.primaryField) {
    console.log(`📝 Will populate primary field: ${evaluationTable.primaryField.name}`);
  }

  // Process each applicant
  return applicants.map(async (applicant) => {
    // Create a progress updater specific to this applicant
    const innerSetProgress: SetProgress = (updater) => {
      setProgress(
        () => 0.1 + (0.9 / applicants.length) * updater(0) // Start at 10% (after precheck)
      );
    };

    // Helper function to get field name from ID
    const getFieldName = (fieldId: string): string => {
      return fieldNameMap.get(fieldId) || fieldId;
    };

    // Convert the applicant record to a plain object
    const plainRecord = convertToPlainRecord(applicant, preset);

    // Fast path: if no fields need evaluation, return minimal result
    if (!hasStandaloneFields && dependencyMap.size === 0) {
      const result: Record<string, unknown> = {};
      result[preset.evaluationApplicantField] = [{ id: applicant.id }];

      // Set applicant name in evaluation record
      setApplicantNameInResult(result, applicant, evaluationTable);

      return result;
    }

    // Determine which fields to skip
    const skipFields = determineSkipFields(dependencyMap, plainRecord, preset);

    // Process the applicant
    const result: Record<string, unknown> = await evaluateApplicant(
      plainRecord,
      preset,
      innerSetProgress,
      skipFields,
      getFieldName // Pass the field name lookup function
    );

    result[preset.evaluationApplicantField] = [{ id: applicant.id }];

    // Set applicant name in evaluation record
    setApplicantNameInResult(result, applicant, evaluationTable);

    return result;
  });
};

const convertToPlainRecord = (
  applicant: AirtableRecord,
  preset: Preset
): Record<string, string> => {
  const record = {};

  for (const field of preset.applicantFields) {
    try {
      // Use the field's questionName if available, otherwise use the field ID as the key
      const key = field.questionName || field.fieldId;

      // Get the value from the Airtable record
      const value = applicant.getCellValueAsString(field.fieldId);

      // Store in our record using the key
      record[key] = value;

      // Also store using the field ID to ensure we can always look it up
      if (key !== field.fieldId) {
        record[field.fieldId] = value;
      }
    } catch (error) {
      console.error(`Error converting field ${field.fieldId}:`, error);
    }
  }

  return record;
};

/**
 * Format applicant data for LLM processing
 *
 * @param applicant Record containing applicant data
 * @returns Formatted string for LLM input
 */
const stringifyApplicantForLLM = (applicant: Record<string, string>): string => {
  return Object.entries(applicant)
    .filter(([, value]) => value)
    .map(([key, value]) => `### ${key}\n\n${value}`)
    .join('\n\n');
};

/**
 * Ensure text fits within Airtable's character limits
 *
 * @param text Text to potentially truncate
 * @param maxLength Maximum allowed length (default: 95000)
 * @returns Truncated text with notice if needed
 */
const truncateForAirtable = (text: string, maxLength = 95000): string => {
  if (text.length <= maxLength) return text;

  const truncationNote =
    "\n\n[CONTENT TRUNCATED: This text was too long for Airtable's limits]";
  return text.substring(0, maxLength - truncationNote.length) + truncationNote;
};

const evaluateApplicant = async (
  applicant: Record<string, string>,
  preset: Preset,
  setProgress: SetProgress,
  skipFields: Set<string> = new Set(), // Fields to skip (faster approach)
  getFieldName: (fieldId: string) => string = (id) => id // Function to get field name from ID
): Promise<Record<string, number | string>> => {
  const logsByField = {};
  const skippedFields = {};
  const applicantString = stringifyApplicantForLLM(applicant);

  const itemResults = await Promise.all(
    preset.evaluationFields.map(async ({ fieldId, criteria }) => {
      // Fast path: check if this field should be skipped based on the pre-computed skipFields
      if (skipFields.has(fieldId)) {
        // Record it as skipped for logging purposes
        skippedFields[fieldId] = 'Skipped because the required input field was empty';

        // Update progress and return null (we'll filter it out later)
        setProgress((prev) => prev + 1 / preset.evaluationFields.length);
        return [fieldId, null] as const;
      }

      // Retry-wrapper around processApplicationPrediction
      // Common failure reasons:
      // - the model doesn't follow instructions to output the ranking in the requested format
      // - the model waffles on too long and hits the token limit
      // - we hit rate limits, or just transient faults
      // Retrying (with exponential backoff) appears to fix these problems

      // Get simplified identifiers for logging
      const applicantId = getApplicantIdentifier(applicant);
      const fieldName = getFieldName(fieldId);

      // Enhanced logging for API calls
      const fieldStartTime = Date.now();
      console.log(`🔄 Starting evaluation: ${fieldName} for ${applicantId}`);

      // Use consistent retry pattern
      const { ranking, transcript } = await pRetry(
        async () => {
          const apiCallStartTime = Date.now();
          console.log(`🌐 Making API call for ${fieldName} (${applicantId})`);

          const result = await evaluateItem(
            applicantString,
            criteria,
            fieldId,
            applicantId,
            fieldName
          );

          const apiCallTime = Date.now() - apiCallStartTime;
          console.log(
            `✅ API call completed for ${fieldName} (${applicantId}) in ${apiCallTime}ms - Ranking: ${result.ranking}`
          );

          return result;
        },
        {
          retries: 3,
          factor: 2,
          minTimeout: 1000,
          maxTimeout: 5000,
          // Enhanced error logging with retry information
          onFailedAttempt: (error) => {
            const apiCallTime = Date.now() - fieldStartTime;
            console.error(
              `🔄 Retry ${error.attemptNumber} for ${fieldName} (${applicantId}) ` +
                `after ${apiCallTime}ms - ${error.message}`
            );
          },
        }
      );

      const fieldTotalTime = Date.now() - fieldStartTime;
      console.log(
        `✅ Completed evaluation: ${fieldName} for ${applicantId} in ${fieldTotalTime}ms`
      );

      // Truncate each individual transcript to avoid exceeding Airtable limits
      logsByField[fieldId] = truncateForAirtable(
        `# ${fieldId}\n\n${transcript}`,
        30000
      );

      setProgress((prev) => prev + 1 / preset.evaluationFields.length);
      return [fieldId, ranking] as const;
    })
  );

  // Filter out null results (skipped evaluations) so they don't appear in the output record
  // Use a simple loop for better performance with large arrays
  const combined: Record<string, number | string> = {};
  for (const [fieldId, value] of itemResults) {
    if (value !== null) {
      combined[fieldId] = value;
    }
  }

  // Add skip information to the logs
  if (preset.evaluationLogsField) {
    // First combine all field logs
    let logs = preset.evaluationFields
      .map(({ fieldId }) => {
        // Add skipped field information if applicable
        if (skippedFields[fieldId]) {
          return `# ${fieldId}\n\n## SKIPPED\n\n${skippedFields[fieldId]}`;
        }

        return logsByField[fieldId];
      })
      .join('\n\n');

    // Ensure the combined logs also fit within Airtable's limits
    logs = truncateForAirtable(logs);
    combined[preset.evaluationLogsField] = logs;
  }

  return combined;
};

/**
 * Helper to build error context string for ranking errors
 */
const buildRankingErrorContext = (
  rankingKeyword: string,
  fieldIdentifier?: string,
  applicantIdentifier?: string
): string => {
  let context = `(${rankingKeyword})`;
  if (fieldIdentifier) context += ` for field "${fieldIdentifier}"`;
  if (applicantIdentifier) context += ` for applicant "${applicantIdentifier}"`;
  return context;
};

/**
 * Validates that a parsed ranking value is an integer within the 1-5 range
 */
const validateRankingValue = (
  rawValue: string,
  parsedInt: number,
  context: string
): void => {
  if (Math.abs(parsedInt - Number.parseFloat(rawValue)) > 0.01) {
    throw new Error(`Non-integer final ranking: ${rawValue} ${context}`);
  }

  if (parsedInt < 1 || parsedInt > 5) {
    throw new Error(`Rating ${parsedInt} is out of range (must be 1-5) ${context}`);
  }
};

// TODO: test if returning response in JSON is better
const extractFinalRanking = (
  text: string,
  rankingKeyword = 'FINAL_RANKING',
  fieldIdentifier?: string,
  applicantIdentifier?: string
): number => {
  const regex = new RegExp(`${rankingKeyword}\\s*=\\s*([\\d\\.]+)`);
  const match = text.match(regex);
  const context = buildRankingErrorContext(
    rankingKeyword,
    fieldIdentifier,
    applicantIdentifier
  );

  if (!match?.[1]) {
    throw new Error(`Missing final ranking ${context}`);
  }

  const parsedInt = Number.parseInt(match[1]);
  validateRankingValue(match[1], parsedInt, context);

  return parsedInt;
};

const evaluateItem = async (
  applicantString: string,
  criteriaString: string,
  fieldIdentifier?: string, // Add optional field identifier for better error logging
  applicantIdentifier?: string, // Add optional applicant identifier for better error logging
  fieldName?: string // Add optional human-readable field name
): Promise<{
  transcript: string;
  ranking: number;
}> => {
  // Convert explicit line breaks to actual line breaks in the criteria (since they come from an HTML input)
  const processedCriteriaString = criteriaString.replace(/<br>/g, '\n');

  // Get current prompt settings and template
  const settings = getPromptSettings();
  const template = getActiveTemplate();

  // Check if server mode is enabled
  if (isServerModeEnabled()) {
    try {
      // Use the server's evaluation endpoint
      console.log(`Using server evaluation endpoint for ${fieldName || fieldIdentifier}`);
      
      const result = await evaluateApplicantWithServer(
        applicantString,
        processedCriteriaString,
        settings.selectedTemplate,
        settings.rankingKeyword,
        settings.additionalInstructions
      );
      
      // If server evaluation returned a score, use it
      if (result.score !== null) {
        // Create a transcript for consistency with direct mode
        const transcript = [
          `## user\n\n${applicantString}`,
          `## system\n\n${template.systemMessage}`,
          `## assistant\n\n${result.result}`
        ].join('\n\n');
        
        return {
          transcript,
          ranking: result.score
        };
      }
      
      // If server evaluation failed or returned null score, fall back to direct mode
      console.log(`Server evaluation failed or returned null score, falling back to direct mode for ${fieldName || fieldIdentifier}`);
    } catch (error) {
      // Log the error and fall back to direct mode
      console.error(`Error using server evaluation, falling back to direct mode: ${error.message}`);
    }
  }
  
  // Direct mode evaluation (original implementation)
  // Build prompt using the template system
  const promptConfig = {
    template,
    variables: {
      criteriaString: processedCriteriaString,
      rankingKeyword: settings.rankingKeyword,
      additionalInstructions: settings.additionalInstructions,
    },
  };

  const prompt = buildPrompt(applicantString, promptConfig);
  const rankingKeyword = getRankingKeyword(promptConfig);

  // Reduce debug logging to just essentials
  const completion = await getChatCompletion(prompt);

  // Create a clean transcript format
  const transcript = [...prompt, { role: 'assistant', content: completion }]
    .map((message) => `## ${message.role}\n\n${message.content}`)
    .join('\n\n');

  try {
    // Try to extract the ranking, if it fails it will throw an error
    const ranking = extractFinalRanking(
      completion,
      rankingKeyword, // Use dynamic ranking keyword from settings
      fieldName || fieldIdentifier, // Use the human-readable field name if available
      applicantIdentifier
    );

    return {
      transcript,
      ranking,
    };
  } catch (error) {
    // Always log the full LLM response when the ranking extraction fails
    console.group(`📋 Full LLM Response for ${fieldName || fieldIdentifier}:`);
    console.log('Error:', error.message);
    console.log(completion);
    console.groupEnd();

    // Re-throw the error so it can be handled by the retry mechanism
    throw error;
  }
};
