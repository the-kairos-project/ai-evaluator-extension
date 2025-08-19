import type { Record as AirtableRecord, Table } from '@airtable/blocks/models';
import { Logger } from './logger';
import pRetry from 'p-retry';
import { getChatCompletion } from './getChatCompletion';
import { isServerModeEnabled, evaluateApplicantWithServer, resetServerFallbackPrompt } from './getChatCompletion/server';
import { createEvaluationRecords } from './evaluation/airtableWriter';

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
): Map<string, string[]> => {
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

  return dependencyMap;
};

/**
 * Process a batch of applicants
 */
export async function processBatch(
  applicantRecords: AirtableRecord[],
  preset: Preset,
  evaluationTable: Table,
  setProgress: SetProgress,
  setResult: (result: string) => void,
  batchNumber: number,
  batchStartIndex: number = 0
): Promise<{ successes: number; failures: number }> {
  // Fast path: if empty, nothing to process
  if (!applicantRecords.length || !preset.evaluationFields.length) {
    return { successes: 0, failures: 0 };
  }

  // Reset server-fallback prompt state so we only ask once per batch
  try {
    resetServerFallbackPrompt();
  } catch (e) {
    // Non-fatal if reset isn't available for some reason
  }

  // Get field names for better error messages
  const fieldNameMap =
    applicantRecords.length > 0
      ? getFieldNames(applicantRecords[0], preset)
      : new Map<string, string>();

  // Log basic processing info
  Logger.info(
    `Processing ${applicantRecords.length} applicants with ${preset.evaluationFields.length} evaluation fields`
  );

  // Log enrichment field configuration
  Logger.info("📊 Enrichment field configuration from preset:", {
    linkedinDataField: preset.linkedinDataField,
    pdfResumeDataField: preset.pdfResumeDataField,
    useLinkedinEnrichment: preset.useLinkedinEnrichment,
    usePdfResumeEnrichment: preset.usePdfResumeEnrichment
  });

  // Analyze field dependencies
  Logger.debug("Multi-axis output field configuration from preset:", {
    multiAxisDataField: preset.multiAxisDataField,
    generalPromiseField: preset.generalPromiseField,
    mlSkillsField: preset.mlSkillsField,
    softwareEngineeringField: preset.softwareEngineeringField,
    policyExperienceField: preset.policyExperienceField,
    aiSafetyUnderstandingField: preset.aiSafetyUnderstandingField,
    pathToImpactField: preset.pathToImpactField,
    researchExperienceField: preset.researchExperienceField
  });
  const dependencyMap = buildDependencyMap(preset);
  const hasStandaloneFields = preset.evaluationFields.some(
    (field) => !field.dependsOnInputField
  );

  // Process each applicant
  let successCount = 0;
  let failureCount = 0;

  for (let i = 0; i < applicantRecords.length; i++) {
    const applicantRecord = applicantRecords[i];
    const applicantIndex = i;
    const totalApplicantIndex = batchStartIndex + i;
    const applicantName = applicantRecord.name || applicantRecord.id;

    Logger.info(
      `🚀 Starting processing of applicant ${totalApplicantIndex + 1} (index ${applicantIndex} in batch ${batchNumber})`
    );

    // Create a progress updater specific to this applicant
    const innerSetProgress: SetProgress = (updater) => {
      setProgress(
        () => 0.1 + (0.9 / applicantRecords.length) * updater(0) // Start at 10% (after precheck)
      );
    };

    try {
      // Convert the applicant record to a plain object
      const plainRecord = convertToPlainRecord(applicantRecord, preset);

      // Fast path: if no fields need evaluation, return minimal result
      if (!hasStandaloneFields && dependencyMap.size === 0) {
        const result: Record<string, string | number> = {};
        result[preset.evaluationApplicantField] = applicantRecord.id as string;

        // Set applicant name in evaluation record
        setApplicantNameInResult(result, applicantRecord, evaluationTable);

        // Create evaluation record
        await createEvaluationRecords(
          evaluationTable,
          applicantRecord,
          preset.evaluationApplicantField,
          preset.evaluationLogsField,
          preset.linkedinDataField, // Add LinkedIn data field
          preset.pdfResumeDataField, // Add PDF resume data field
          preset.multiAxisDataField, // Add multi-axis data field
          // Individual axis fields
          preset.generalPromiseField,
          preset.mlSkillsField,
          preset.softwareEngineeringField,
          preset.policyExperienceField,
          preset.aiSafetyUnderstandingField,
          preset.pathToImpactField,
          preset.researchExperienceField,
          result,
          {} // No logs for this fast path
        );

        Logger.info(`Skipped evaluation for ${applicantName} due to no evaluation fields.`);
        successCount++;
        continue;
      }

      // Determine which fields to skip based on dependencies
      const skipFields = new Set<string>();
      for (const [dependencyField, dependentFields] of dependencyMap.entries()) {
        if (!plainRecord[dependencyField]) {
          // If dependency field is empty, skip all dependent fields
          for (const fieldId of dependentFields) {
            skipFields.add(fieldId);
          }
        }
      }

      // Evaluate the applicant
      const evalResult = await evaluateApplicant(
        plainRecord,
        preset,
        innerSetProgress,
        skipFields,
        (id) => fieldNameMap.get(id) || id
      );

      // Create a result object for Airtable
      const result: Record<string, string | number> = {};
      for (const [fieldId, value] of Object.entries(evalResult)) {
        if (typeof value === 'number' || typeof value === 'string') {
          result[fieldId] = value;
        }
      }

      result[preset.evaluationApplicantField] = applicantRecord.id as string;

      // Set applicant name in evaluation record
      setApplicantNameInResult(result, applicantRecord, evaluationTable);

      // Extract logs and enrichment data from evaluation result
      const logsByField: Record<string, string> = {};
      if (typeof evalResult === 'object' && evalResult !== null) {
        // First, check if we have a raw_server_response property that contains the full server response
        // This would be present if we used server mode evaluation
        if ('raw_server_response' in evalResult && typeof evalResult.raw_server_response === 'string') {
          Logger.debug(`📋 Found raw server response, length: ${evalResult.raw_server_response.length}`);
          
          // Use a special key for the raw response to ensure it's processed for extraction
          logsByField['_raw_response'] = evalResult.raw_server_response;
          
          // Debug: show snippet of raw server response to help trace enrichment markers
          try {
            Logger.info('🔎 raw_server_response snippet:', evalResult.raw_server_response.substring(0, 500));
            Logger.info('🔎 raw_server_response contains markers:', {
              linkedin: evalResult.raw_server_response.includes('[LINKEDIN_DATA]'),
              pdf: evalResult.raw_server_response.includes('[PDF_RESUME_DATA]'),
              enrichmentLog: evalResult.raw_server_response.includes('[ENRICHMENT LOG]'),
              multiAxis: evalResult.raw_server_response.includes('[MULTI_AXIS_SCORES]')
            });
          } catch (e) {
            Logger.info('🔎 Failed to log raw_server_response snippet', e);
          }
          // Check if this response contains enrichment data
          Logger.debug(`🔍 Checking raw response for enrichment data markers`);
          Logger.debug(`🔍 Contains [LINKEDIN_DATA]: ${evalResult.raw_server_response.includes('[LINKEDIN_DATA]')}`);
          Logger.debug(`🔍 Contains [PDF_RESUME_DATA]: ${evalResult.raw_server_response.includes('[PDF_RESUME_DATA]')}`);
        }
        
        // Then process regular transcript fields
        for (const [key, value] of Object.entries(evalResult)) {
          if (typeof value === 'string') {
            // Check if this is a transcript (contains user and assistant sections)
            if (value.includes('## user') && value.includes('## assistant')) {
              Logger.debug(`📋 Found transcript for field ${key}, length: ${value.length}`);
              logsByField[key] = value;
              // Debug: log presence of enrichment markers in this transcript
              try {
                Logger.info(`🔎 transcript ${key} markers:`, {
                  linkedin: value.includes('[LINKEDIN_DATA]'),
                  pdf: value.includes('[PDF_RESUME_DATA]'),
                  enrichmentLog: value.includes('[ENRICHMENT LOG]'),
                  multiAxis: value.includes('[MULTI_AXIS_SCORES]')
                });
                Logger.info(`🔎 transcript ${key} snippet:`, value.substring(0, 300));
              } catch (e) {
                Logger.info(`🔎 Failed to inspect transcript ${key}`, e);
              }
              
              // Check if this transcript contains enrichment data
              Logger.debug(`🔍 Checking transcript for enrichment data markers in field ${key}`);
              Logger.debug(`🔍 Contains [LINKEDIN_DATA]: ${value.includes('[LINKEDIN_DATA]')}`);
              Logger.debug(`🔍 Contains [PDF_RESUME_DATA]: ${value.includes('[PDF_RESUME_DATA]')}`);
            }
          }
        }
      }

      // Create evaluation record
      await createEvaluationRecords(
        evaluationTable,
        applicantRecord,
        preset.evaluationApplicantField,
        preset.evaluationLogsField,
        preset.linkedinDataField,
        preset.pdfResumeDataField,
        preset.multiAxisDataField,
        // Individual axis fields
        preset.generalPromiseField,
        preset.mlSkillsField,
        preset.softwareEngineeringField,
        preset.policyExperienceField,
        preset.aiSafetyUnderstandingField,
        preset.pathToImpactField,
        preset.researchExperienceField,
        result,
        logsByField
      );

      Logger.info(`Completed evaluation for ${applicantName}`);
      successCount++;
    } catch (error) {
      Logger.error(`Error processing applicant ${applicantName}:`, error);
      failureCount++;
    }
  }

  return { successes: successCount, failures: failureCount };
}

/**
 * Compatibility function to maintain the original API that MainPage.tsx depends on
 * @returns array of promises, each expected to return an evaluation
 */
export const evaluateApplicants = (
  applicants: AirtableRecord[],
  preset: Preset,
  setProgress: SetProgress,
  evaluationTable?: Table
): Promise<Record<string, unknown>>[] => {
  // Return an array of promises, one for each applicant
  return applicants.map(async (applicant) => {
    try {
      // Convert the applicant record to a plain object
      const plainRecord = convertToPlainRecord(applicant, preset);
      
        // Get LinkedIn URL if enrichment is enabled
  let linkedinUrl: string | undefined;
  if (preset.useLinkedinEnrichment && preset.linkedinUrlField && plainRecord[preset.linkedinUrlField]) {
    linkedinUrl = plainRecord[preset.linkedinUrlField];
    Logger.debug(`🔍 LinkedIn enrichment enabled for applicant with URL: ${linkedinUrl}`);
  } else if (preset.useLinkedinEnrichment) {
    Logger.warn(`⚠️ LinkedIn enrichment enabled but no URL found in field`);
  }
  
  // Get PDF resume URL if enrichment is enabled
  let pdfResumeUrl: string | undefined;
  if (preset.usePdfResumeEnrichment && preset.pdfResumeField) {
    try {
      const fieldValue = plainRecord[preset.pdfResumeField];
      
      if (fieldValue) {
        // Direct string value (URL or text field)
        if (typeof fieldValue === 'string') {
          pdfResumeUrl = fieldValue;
        } 
        // Attachment field (array of objects with url and filename)
        else if (Array.isArray(fieldValue)) {
          if (fieldValue.length > 0) {
            // Find the first PDF attachment
            const pdfAttachment = fieldValue.find(att => 
              att.filename && typeof att.filename === 'string' && 
              att.filename.toLowerCase().endsWith('.pdf')
            );
            
            if (pdfAttachment && pdfAttachment.url) {
              pdfResumeUrl = pdfAttachment.url;
            } else if (fieldValue[0] && fieldValue[0].url) {
              // Fallback to first attachment if no PDF is found
              pdfResumeUrl = fieldValue[0].url;
            }
          }
        }
      }
      
      if (pdfResumeUrl) {
        Logger.debug(`📄 PDF resume enrichment enabled with URL: ${pdfResumeUrl}`);
      } else {
        Logger.warn(`⚠️ PDF resume field selected but no valid PDF found`);
      }
    } catch (error) {
      Logger.error(`Error accessing PDF resume field: ${error.message}`);
    }
  } else if (preset.usePdfResumeEnrichment) {
    Logger.warn(`⚠️ PDF resume enrichment enabled but no field selected`);
  }
      
      // Create a result object for Airtable
      const result: Record<string, unknown> = {};
      
      // Evaluate each field
      const fieldPromises = preset.evaluationFields.map(async ({ fieldId, criteria }) => {
        try {
          const fieldName = fieldId; // Simplified for compatibility
          const applicantId = getApplicantIdentifier(plainRecord);
          
      const evalResult = await evaluateItem(
            stringifyApplicantForLLM(plainRecord),
            criteria,
            fieldId,
            applicantId,
            fieldName,
        linkedinUrl,
        pdfResumeUrl,
        preset.useMultiAxisEvaluation // Pass multi-axis evaluation flag
      );
          
          result[fieldId] = evalResult.ranking;
          
          // If we have a logs field, add the transcript
          if (preset.evaluationLogsField) {
            if (!result[preset.evaluationLogsField]) {
              result[preset.evaluationLogsField] = '';
            }
            result[preset.evaluationLogsField] += `## Field: ${fieldId}\n\n${evalResult.transcript}\n\n---\n\n`;
          }
          
          // Update progress
          setProgress((prev) => prev + 1 / (preset.evaluationFields.length * applicants.length));
          
          return evalResult;
        } catch (error) {
          Logger.error(`Error evaluating field ${fieldId}:`, error);
          return null;
        }
      });
      // Await all evaluations and capture results for multi-axis mapping
      const evalResults = await Promise.all(fieldPromises);

      // If multi-axis evaluation is enabled, map axis scores to individual fields
      if (preset.useMultiAxisEvaluation && evalResults.length > 0 && evalResults[0]?.multi_axis_scores) {
        const multiAxisScores = evalResults[0].multi_axis_scores as Array<{name: string, score: number | null}>;
        Logger.debug("🔄 Compatibility mapping of multi-axis scores:", multiAxisScores);
        multiAxisScores.forEach(axisScore => {
          const scoreVal = axisScore.score;
          if (scoreVal !== null) {
            switch (axisScore.name) {
              case "General Promise":
                if (preset.generalPromiseField) result[preset.generalPromiseField] = scoreVal;
                break;
              case "ML Skills":
                if (preset.mlSkillsField) result[preset.mlSkillsField] = scoreVal;
                break;
              case "Software Engineering Skills":
                if (preset.softwareEngineeringField) result[preset.softwareEngineeringField] = scoreVal;
                break;
              case "Policy Experience":
                if (preset.policyExperienceField) result[preset.policyExperienceField] = scoreVal;
                break;
              case "Understanding of AI Safety":
                if (preset.aiSafetyUnderstandingField) result[preset.aiSafetyUnderstandingField] = scoreVal;
                break;
              case "Path to Impact":
                if (preset.pathToImpactField) result[preset.pathToImpactField] = scoreVal;
                break;
              case "Research Experience":
                if (preset.researchExperienceField) result[preset.researchExperienceField] = scoreVal;
                break;
            }
          }
        });
      }
      // Set the applicant link
      result[preset.evaluationApplicantField] = [{ id: applicant.id }];
      
      // Set applicant name in evaluation record
      setApplicantNameInResult(result, applicant, evaluationTable);
      
      return result;
    } catch (error) {
      Logger.error(`Error processing applicant ${applicant.id}:`, error);
      throw error;
    }
  });
};

const convertToPlainRecord = (
  applicant: AirtableRecord,
  preset: Preset
): Record<string, string | any> => {
  const record = {};

  // Process all regular applicant fields
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
      Logger.error(`Error converting field ${field.fieldId}:`, error);
    }
  }

  // Process LinkedIn URL field if enabled
  if (preset.useLinkedinEnrichment && preset.linkedinUrlField) {
    try {
      const linkedinValue = applicant.getCellValueAsString(preset.linkedinUrlField);
      if (linkedinValue) {
        record[preset.linkedinUrlField] = linkedinValue;
      }
    } catch (error) {
      Logger.error(`Error getting LinkedIn URL field: ${error.message}`);
    }
  }

  // Process PDF resume field if enabled
  if (preset.usePdfResumeEnrichment && preset.pdfResumeField) {
    try {
      // For text/URL fields
      try {
        const pdfValue = applicant.getCellValueAsString(preset.pdfResumeField);
        if (pdfValue) {
          record[preset.pdfResumeField] = pdfValue;
        }
      } catch (e) {
        // Not a string field, try as attachment
      }
      
      // For attachment fields
      try {
        const attachmentValue = applicant.getCellValue(preset.pdfResumeField);
        if (attachmentValue && Array.isArray(attachmentValue) && attachmentValue.length > 0) {
          record[preset.pdfResumeField] = attachmentValue;
        }
      } catch (e) {
        Logger.error(`Error accessing attachment: ${e.message}`);
      }
    } catch (error) {
      Logger.error(`Error getting PDF resume field: ${error.message}`);
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
    // TODO: This is a quick fix to filter out duplicate field IDs. The proper solution would be
    // to refactor convertToPlainRecord to avoid storing both field IDs and questionNames,
    // while maintaining a separate lookup mechanism for field IDs when needed for dependencies
    // and enrichment fields.
    // Filter out entries where key matches Airtable field ID pattern
    .filter(([key]) => !key.match(/^fld[A-Za-z0-9]+$/))
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
  
  // Get LinkedIn URL if enrichment is enabled
  let linkedinUrl: string | undefined;
  if (preset.useLinkedinEnrichment && preset.linkedinUrlField && applicant[preset.linkedinUrlField]) {
    linkedinUrl = applicant[preset.linkedinUrlField];
    Logger.debug(`🔍 LinkedIn enrichment enabled for applicant with URL: ${linkedinUrl}`);
  } else if (preset.useLinkedinEnrichment) {
    Logger.warn(`⚠️ LinkedIn enrichment enabled but no URL found in field`);
  }
  
  // Get PDF resume URL if enrichment is enabled
  let pdfResumeUrl: string | undefined;
  
  if (preset.usePdfResumeEnrichment && preset.pdfResumeField) {
    try {
      const fieldValue = applicant[preset.pdfResumeField];
      
      if (fieldValue) {
        // Case 1: Direct string value (URL or text field)
        if (typeof fieldValue === 'string') {
          pdfResumeUrl = fieldValue;
          Logger.debug(`📄 PDF resume URL found in text/URL field: ${pdfResumeUrl}`);
        } 
        // Case 2: Attachment field (array of objects with url and filename)
        else if (Array.isArray(fieldValue)) {
          try {
            // Properly type the attachment array
            interface AirtableAttachment {
              id: string;
              url: string;
              filename: string;
              size: number;
              type: string;
            }
            
            const attachments = fieldValue as unknown as AirtableAttachment[];
            
            if (attachments.length > 0) {
              // Find the first PDF attachment
              const pdfAttachment = attachments.find(att => 
                att.filename && typeof att.filename === 'string' && 
                att.filename.toLowerCase().endsWith('.pdf')
              );
              
              if (pdfAttachment && pdfAttachment.url) {
                pdfResumeUrl = pdfAttachment.url;
                Logger.debug(`📄 PDF resume attachment found: ${pdfAttachment.filename}`);
              } else if (attachments[0] && attachments[0].url) {
                // Fallback to first attachment if no PDF is found
                pdfResumeUrl = attachments[0].url;
                Logger.debug(`📄 Using first attachment: ${attachments[0].filename || 'unnamed'}`);
              }
            }
          } catch (attachmentError) {
            Logger.error(`Error processing attachment data: ${attachmentError.message}`);
          }
        }
      }
      
      if (pdfResumeUrl) {
        Logger.debug(`📄 PDF resume enrichment enabled for applicant with URL: ${pdfResumeUrl}`);
      } else {
        Logger.warn(`⚠️ PDF resume field selected but no valid PDF found`);
      }
    } catch (error) {
      Logger.error(`Error accessing PDF resume field: ${error.message}`);
    }
  } else if (preset.usePdfResumeEnrichment) {
    Logger.warn(`⚠️ PDF resume enrichment enabled but no field selected`);
  }

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
      Logger.debug(`🔄 Starting evaluation: ${fieldName} for ${applicantId}`);

      // Use consistent retry pattern
      const { ranking, transcript } = await pRetry(
        async () => {
          const apiCallStartTime = Date.now();
          Logger.debug(`🌐 Making API call for ${fieldName} (${applicantId})`);

          const result = await evaluateItem(
            applicantString,
            criteria,
            fieldId,
            applicantId,
            fieldName,
            linkedinUrl, // Pass LinkedIn URL to evaluateItem
            pdfResumeUrl, // Pass PDF resume URL to evaluateItem
            preset.useMultiAxisEvaluation // Pass multi-axis flag to evaluateItem
          );

          const apiCallTime = Date.now() - apiCallStartTime;
          Logger.debug(
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
            Logger.error(
              `🔄 Retry ${error.attemptNumber} for ${fieldName} (${applicantId}) ` +
                `after ${apiCallTime}ms - ${error.message}`
            );
          },
        }
      );

      const fieldTotalTime = Date.now() - fieldStartTime;
      Logger.debug(
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
  fieldIdentifier?: string, // Optional field identifier for better error logging
  applicantIdentifier?: string, // Optional applicant identifier for better error logging
  fieldName?: string, // Optional human-readable field name
  linkedinUrl?: string, // Optional LinkedIn URL for enrichment
  pdfResumeUrl?: string, // Optional PDF resume URL for enrichment
  useMultiAxis?: boolean // Optional flag for multi-axis evaluation
): Promise<{
  transcript: string;
  ranking: number;
  raw_server_response?: string; // Add optional raw_server_response property
  multi_axis_scores?: Array<{name: string, score: number | null}>; // Add multi-axis scores property
}> => {
  // Add detailed logging for enrichment URLs
  Logger.debug("🔄 Evaluating item with enrichment:", {
    hasLinkedinUrl: !!linkedinUrl,
    linkedinUrl: linkedinUrl ? (linkedinUrl.length > 30 ? linkedinUrl.substring(0, 30) + "..." : linkedinUrl) : null,
    hasPdfResumeUrl: !!pdfResumeUrl,
    pdfResumeUrl: pdfResumeUrl ? (pdfResumeUrl.length > 30 ? pdfResumeUrl.substring(0, 30) + "..." : pdfResumeUrl) : null,
    fieldIdentifier,
    fieldName
  });

  // Convert explicit line breaks to actual line breaks in the criteria (since they come from an HTML input)
  const processedCriteriaString = criteriaString.replace(/<br>/g, '\n');

  // Get current prompt settings and template
  const settings = getPromptSettings();
  const template = getActiveTemplate();

  // Check if server mode is enabled
  if (isServerModeEnabled()) {
    try {
      // Use the server's evaluation endpoint
      Logger.debug(`Using server evaluation endpoint for ${fieldName || fieldIdentifier}`);
      
      const result = await evaluateApplicantWithServer(
        applicantString,
        processedCriteriaString,
        linkedinUrl, // Optional LinkedIn URL
        pdfResumeUrl, // Optional PDF URL
        useMultiAxis // Multi-axis flag
      );
      
      // If server evaluation returned a score, use it
      if (result.score !== null) {
        Logger.debug("🔄 Evaluation response received, transcript length:", result.result.length);
        Logger.debug("🔄 Looking for enrichment data in response...");
        Logger.debug("🔄 Contains [LINKEDIN_DATA]:", result.result.includes("[LINKEDIN_DATA]"));
        Logger.debug("🔄 Contains [PDF_RESUME_DATA]:", result.result.includes("[PDF_RESUME_DATA]"));
        Logger.debug("🔄 Contains [ENRICHMENT LOG]:", result.result.includes("[ENRICHMENT LOG]"));
        
        // Store the raw server response in a variable for later use
        const rawServerResponse = result.result;
        
        // Create a transcript for consistency with direct mode
        const transcript = [
          `## user\n\n${applicantString}`,
          `## system\n\n${template.systemMessage}`,
          `## assistant\n\n${rawServerResponse}`
        ].join('\n\n');
        
        // Create a special property to hold the raw server response
        // This will be used to extract LinkedIn and PDF data
        // Check if we have multi-axis scores in the result
        if (result.scores && Array.isArray(result.scores)) {
          Logger.debug('🎯 Multi-axis scores found in response:', result.scores);
          // Extract multi-axis data and format for display
          // No need to create a variable here, we'll use result.scores directly
          
          return {
            transcript,
            ranking: result.score,
            // Add raw response as a separate property so it gets included in evalResult
            raw_server_response: rawServerResponse,
            // Add multi-axis scores
            multi_axis_scores: result.scores
          };
        } else {
          return {
            transcript,
            ranking: result.score,
            // Add raw response as a separate property so it gets included in evalResult
            raw_server_response: rawServerResponse
          };
        }
      }
      
      // If server evaluation failed or returned null score, fall back to direct mode
      Logger.debug(`Server evaluation failed or returned null score, falling back to direct mode for ${fieldName || fieldIdentifier}`);
    } catch (error) {
      // Log the error and fall back to direct mode
      Logger.error(`Error using server evaluation, falling back to direct mode: ${error.message}`);
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
    Logger.error(`Error extracting ranking: ${error.message}`);
    Logger.error(`Full response: ${completion.substring(0, 200)}...`);
    
    // Re-throw the error so it can be handled by the retry mechanism
    throw error;
  }
};