import { Record as AirtableRecord } from "@airtable/blocks/models";
import { Preset } from "./preset";
import { Prompt } from "./getChatCompletion";
import { getChatCompletion } from "./getChatCompletion/openai";
import pRetry from "p-retry";

export type SetProgress = (updater: (prev: number) => number) => void;

/**
 * @returns array of promises, each expected to return an evaluation
 */
// Maintain a mapping of field IDs to field names for better error reporting
interface FieldMapping {
  id: string;
  name: string;
}

export const evaluateApplicants = (
  applicants: AirtableRecord[],
  preset: Preset,
  setProgress: SetProgress,
): Promise<Record<string, unknown>>[] => {
  // Create a field name mapping for better error messages
  const fieldNameMap = new Map<string, string>();
  
  // Get field names from the applicant 
  try {
    // Use the first applicant to get field names (all applicants have the same fields)
    if (applicants.length > 0) {
      const firstApplicant = applicants[0];
      const table = firstApplicant.parentTable;
      
      // Map all evaluation field IDs to their names
      preset.evaluationFields.forEach(({ fieldId }) => {
        try {
          const field = table.getFieldById(fieldId);
          if (field) {
            fieldNameMap.set(fieldId, field.name);
          }
        } catch (e) {
          // Silently continue - we'll use the ID if the name is not available
        }
      });
    }
  } catch (e) {
    console.warn("Could not get field names for better error messages:", e);
  }
  console.log(
    `Evaluating ${applicants.length} applicants with ${preset.evaluationFields.length} fields each`,
  );

  // Preprocess dependency information for faster checks
  const dependencyMap = new Map<string, string[]>();

  // For each evaluation field that has a dependency, record that information
  preset.evaluationFields.forEach(({ fieldId, dependsOnInputField }) => {
    if (dependsOnInputField) {
      // Store the mapping from input field to dependent output fields
      if (!dependencyMap.has(dependsOnInputField)) {
        dependencyMap.set(dependsOnInputField, []);
      }
      dependencyMap.get(dependsOnInputField).push(fieldId);
    }
  });

  // Check if any fields need to be evaluated at all
  const hasFieldsToEvaluate = preset.evaluationFields.some(
    ({ dependsOnInputField }) => !dependsOnInputField,
  );

  if (dependencyMap.size > 0) {
    console.log(
      `Created dependency map for ${dependencyMap.size} input fields`,
    );
  }

  // Optimize by using an array
  return applicants.map(async (applicant) => {
    // Create a progress updater specific to this applicant
    const innerSetProgress: SetProgress = (updater) => {
      setProgress(
        (progress) => 0.1 + (0.9 / applicants.length) * updater(0), // Start at 10% (after precheck)
      );
    };
    
    // Helper function to get field name from ID
    const getFieldName = (fieldId: string): string => {
      return fieldNameMap.get(fieldId) || fieldId;
    };

    // Convert the applicant record to a plain object - minimal work
    const plainRecord = convertToPlainRecord(applicant, preset);

    // Fast path: if no fields need evaluation (all are dependent), return empty result
    if (!hasFieldsToEvaluate && dependencyMap.size === 0) {
      const result: Record<string, unknown> = {};
      result[preset.evaluationApplicantField] = [{ id: applicant.id }];
      return result;
    }

    // Quick check if any dependency fields are empty before doing detailed work
    const skipFields = new Set<string>();

    // Process all dependencies in one go
    dependencyMap.forEach((dependentFields, inputFieldId) => {
      // Get the value from the plain record
      const key =
        preset.applicantFields.find((f) => f.fieldId === inputFieldId)
          ?.questionName || inputFieldId;
      const value = plainRecord[key] || plainRecord[inputFieldId] || "";

      // If empty, mark all dependent fields to be skipped
      if (!value || value.trim() === "") {
        dependentFields.forEach((fieldId) => skipFields.add(fieldId));
      }
    });

    // Process the applicant
    const result: Record<string, unknown> = await evaluateApplicant(
      plainRecord,
      preset,
      innerSetProgress,
      skipFields,
      getFieldName, // Pass the field name lookup function
    );

    result[preset.evaluationApplicantField] = [{ id: applicant.id }];
    return result;
  });
};

const convertToPlainRecord = (
  applicant: AirtableRecord,
  preset: Preset,
): Record<string, string> => {
  const record = {};

  preset.applicantFields.forEach((field) => {
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
  });

  return record;
};

// TODO: test if plain JSON is better
const stringifyApplicantForLLM = (
  applicant: Record<string, string>,
): string => {
  return Object.entries(applicant)
    .filter(([, value]) => value)
    .map(([key, value]) => `### ${key}\n\n${value}`)
    .join("\n\n");
};

// Helper function to truncate text to fit Airtable's limits
// Airtable has a max of 100,000 characters per cell
const truncateForAirtable = (
  text: string,
  maxLength: number = 95000,
): string => {
  if (text.length <= maxLength) return text;

  // If we need to truncate, add a note about it
  const truncationNote =
    "\n\n[CONTENT TRUNCATED: This text was too long for Airtable's limits]";
  return text.substring(0, maxLength - truncationNote.length) + truncationNote;
};

const evaluateApplicant = async (
  applicant: Record<string, string>,
  preset: Preset,
  setProgress: SetProgress,
  skipFields: Set<string> = new Set(), // Fields to skip (faster approach)
  getFieldName: (fieldId: string) => string = (id) => id, // Function to get field name from ID
): Promise<Record<string, number | string>> => {
  const logsByField = {};
  const skippedFields = {};
  const applicantString = stringifyApplicantForLLM(applicant);

  const itemResults = await Promise.all(
    preset.evaluationFields.map(async ({ fieldId, criteria }) => {
      // Fast path: check if this field should be skipped based on the pre-computed skipFields
      if (skipFields.has(fieldId)) {
        // Record it as skipped for logging purposes
        skippedFields[fieldId] =
          `Skipped because the required input field was empty`;

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
      
      // Get applicant identifier for better error logging
      const applicantIdentifier = Object.entries(applicant)
        .find(([key, value]) => key.toLowerCase().includes('name') || key.toLowerCase().includes('id'))?.[1] || 'unknown';
      
      // Get the field name for better logging
      const fieldName = getFieldName(fieldId);
      
      console.debug(`Processing record for criteria ${fieldName} (applicant: ${applicantIdentifier})`);
      const { ranking, transcript } = await pRetry(
        async () => evaluateItem(applicantString, criteria, fieldId, applicantIdentifier, fieldName),
        {
          onFailedAttempt: (error) =>
            console.error(
              `Failed processing record on attempt ${error.attemptNumber} for field "${fieldName}" (${fieldId}) for applicant "${applicantIdentifier}": `,
              error,
            ),
        },
      );

      // Truncate each individual transcript to avoid exceeding Airtable limits
      logsByField[fieldId] = truncateForAirtable(
        `# ${fieldId}\n\n` + transcript,
        30000,
      );

      setProgress((prev) => prev + 1 / preset.evaluationFields.length);
      return [fieldId, ranking] as const;
    }),
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
      .join("\n\n");

    // Ensure the combined logs also fit within Airtable's limits
    logs = truncateForAirtable(logs);
    combined[preset.evaluationLogsField] = logs;
  }

  return combined;
};

// TODO: test if returning response in JSON is better
const extractFinalRanking = (
  text: string,
  rankingKeyword = "FINAL_RANKING",
  fieldIdentifier?: string,
  applicantIdentifier?: string,
): number => {
  // Look for normal rating
  const regex = new RegExp(`${rankingKeyword}\\s*=\\s*([\\d\\.]+)`);
  const match = text.match(regex);

  if (match && match[1]) {
    const asInt = parseInt(match[1]);
    if (Math.abs(asInt - parseFloat(match[1])) > 0.01) {
      throw new Error(
        `Non-integer final ranking: ${match[1]} (${rankingKeyword})${fieldIdentifier ? ` for field "${fieldIdentifier}"` : ''}${applicantIdentifier ? ` for applicant "${applicantIdentifier}"` : ''}`,
      );
    }
    return parseInt(match[1]);
  }

  // No rating found
  throw new Error(`Missing final ranking (${rankingKeyword})${fieldIdentifier ? ` for field "${fieldIdentifier}"` : ''}${applicantIdentifier ? ` for applicant "${applicantIdentifier}"` : ''}`);
};

const evaluateItem = async (
  applicantString: string,
  criteriaString: string,
  fieldIdentifier?: string, // Add optional field identifier for better error logging
  applicantIdentifier?: string, // Add optional applicant identifier for better error logging
  fieldName?: string, // Add optional human-readable field name
): Promise<{
  transcript: string;
  ranking: number;
}> => {
  // Convert explicit line breaks to actual line breaks in the criteria (since they come from an HTML input)
  criteriaString = criteriaString.replace(/<br>/g, "\n");
  const prompt: Prompt = [
    { role: "user", content: applicantString },
    {
      role: "system",
      content: `Evaluate the application above, based on the following rubric: ${criteriaString}

You should ignore general statements or facts about the world, and focus on what the applicant themselves has achieved. You do not need to structure your assessment similar to the answers the user has given.

First explain your reasoning thinking step by step. Then output your final answer by stating 'FINAL_RANKING = ' and then the relevant integer between the minimum and maximum values in the rubric.`,
    },
  ];
  console.debug(prompt);
  const completion = await getChatCompletion(prompt);
  console.debug(completion);
  const transcript = [...prompt, { role: "assistant", content: completion }]
    .map((message) => `## ${message.role}\n\n${message.content}`)
    .join("\n\n");
  const ranking = extractFinalRanking(
    completion, 
    "FINAL_RANKING", 
    fieldName || fieldIdentifier, // Use the human-readable field name if available
    applicantIdentifier
  );
  return {
    transcript,
    ranking,
  };
};
