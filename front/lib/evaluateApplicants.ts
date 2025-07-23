import type { Record as AirtableRecord, Table } from '@airtable/blocks/models';
import { Logger } from './logger';
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
 * Extract LinkedIn data from evaluation result
 */
function extractLinkedinData(result: string): string | null {
  Logger.debug("🔍 Attempting to extract LinkedIn data from string of length:", result.length);
  
  // Try different pattern variations that might appear in the text
  let patterns = [
    /\[LINKEDIN_DATA\]([\s\S]*?)\[END_LINKEDIN_DATA\]/,
    /\[LINKEDIN_DATA\]\s*([\s\S]*?)\s*\[END_LINKEDIN_DATA\]/,
    /\[LINKEDIN_DATA\]\n([\s\S]*?)\n\[END_LINKEDIN_DATA\]/,
    /\[LINKEDIN_DATA\][\r\n]+([\s\S]*?)[\r\n]+\[END_LINKEDIN_DATA\]/
  ];
  
  // Try each pattern
  for (const pattern of patterns) {
    const match = result.match(pattern);
    if (match && match[1]) {
      Logger.debug("🔍 LinkedIn data match found with pattern:", pattern);
      Logger.debug("🔍 LinkedIn data extracted, length:", match[1].trim().length);
      return match[1].trim();
    }
  }
  
  // If we got here, no match was found
  Logger.debug("🔍 LinkedIn data not found with any pattern");
  
  // Log a small excerpt to help debug
  const excerpt = result.substring(0, 200);
  Logger.debug("🔍 First 200 chars of content:", excerpt);
  
  // If result contains [LINKEDIN_DATA] but we couldn't extract it, log the position
  const marker = "[LINKEDIN_DATA]";
  const endMarker = "[END_LINKEDIN_DATA]";
  const markerIndex = result.indexOf(marker);
  const endMarkerIndex = result.indexOf(endMarker);
  
  if (markerIndex !== -1) {
    Logger.debug(`🔍 Found [LINKEDIN_DATA] at position ${markerIndex}, content around it:`, 
      result.substring(Math.max(0, markerIndex - 20), markerIndex + marker.length + 50));
      
    if (endMarkerIndex !== -1) {
      Logger.debug(`🔍 Found [END_LINKEDIN_DATA] at position ${endMarkerIndex}`);
      Logger.debug(`🔍 Distance between markers: ${endMarkerIndex - (markerIndex + marker.length)}`);
    } else {
      Logger.debug("🔍 End marker [END_LINKEDIN_DATA] not found");
    }
  }
  
  return null;
}

/**
 * Extract enrichment logs from evaluation result
 */
function extractEnrichmentLogs(result: string): string | null {
  Logger.debug("📋 Attempting to extract enrichment logs from string of length:", result.length);
  
  // Try different pattern variations that might appear in the text
  let patterns = [
    /\[ENRICHMENT LOG\]([\s\S]*?)\[END ENRICHMENT LOG\]/,
    /\[ENRICHMENT LOG\]\s*([\s\S]*?)\s*\[END ENRICHMENT LOG\]/,
    /\[ENRICHMENT LOG\]\n([\s\S]*?)\n\[END ENRICHMENT LOG\]/,
    /\[ENRICHMENT LOG\][\r\n]+([\s\S]*?)[\r\n]+\[END ENRICHMENT LOG\]/
  ];
  
  // Try each pattern
  for (const pattern of patterns) {
    const match = result.match(pattern);
    if (match && match[1]) {
      Logger.debug("📋 Enrichment logs found with pattern:", pattern);
      Logger.debug("📋 Enrichment logs extracted, length:", match[1].trim().length);
      return match[1].trim();
    }
  }
  
  Logger.debug("📋 No enrichment logs found");
  return null;
}

/**
 * Extract PDF resume data from evaluation result
 */
function extractPdfResumeData(result: string): string | null {
  Logger.debug("📄 Attempting to extract PDF resume data from string of length:", result.length);
  
  // Try different pattern variations that might appear in the text
  let patterns = [
    /\[PDF_RESUME_DATA\]([\s\S]*?)\[END_PDF_RESUME_DATA\]/,
    /\[PDF_RESUME_DATA\]\s*([\s\S]*?)\s*\[END_PDF_RESUME_DATA\]/,
    /\[PDF_RESUME_DATA\]\n([\s\S]*?)\n\[END_PDF_RESUME_DATA\]/,
    /\[PDF_RESUME_DATA\][\r\n]+([\s\S]*?)[\r\n]+\[END_PDF_RESUME_DATA\]/
  ];
  
  // Try each pattern
  for (const pattern of patterns) {
    const match = result.match(pattern);
    if (match && match[1]) {
      Logger.debug("📄 PDF resume data match found with pattern:", pattern);
      Logger.debug("📄 PDF resume data extracted, length:", match[1].trim().length);
      return match[1].trim();
    }
  }
  
  // If we got here, no match was found
  Logger.debug("📄 PDF resume data not found with any pattern");
  
  // Log a small excerpt to help debug
  const excerpt = result.substring(0, 200);
  Logger.debug("📄 First 200 chars of content:", excerpt);
  
  // If result contains [PDF_RESUME_DATA] but we couldn't extract it, log the position
  const marker = "[PDF_RESUME_DATA]";
  const endMarker = "[END_PDF_RESUME_DATA]";
  const markerIndex = result.indexOf(marker);
  const endMarkerIndex = result.indexOf(endMarker);
  
  if (markerIndex !== -1) {
    Logger.debug(`📄 Found [PDF_RESUME_DATA] at position ${markerIndex}, content around it:`, 
      result.substring(Math.max(0, markerIndex - 20), markerIndex + marker.length + 50));
      
    if (endMarkerIndex !== -1) {
      Logger.debug(`📄 Found [END_PDF_RESUME_DATA] at position ${endMarkerIndex}`);
      Logger.debug(`📄 Distance between markers: ${endMarkerIndex - (markerIndex + marker.length)}`);
    } else {
      Logger.debug("📄 End marker [END_PDF_RESUME_DATA] not found");
    }
  }
  
  return null;
}

/**
 * Create evaluation records in Airtable
 */
/**
 * Extract multi-axis scores from eval result
 */
function extractMultiAxisData(result: string, axisScores?: Array<{name: string, score: number | null}>): string | null {
  // If we have axis scores directly, format them
  if (axisScores && Array.isArray(axisScores)) {
    try {
      // Format multi-axis scores as readable text
      let formattedData = "## Multi-Axis Evaluation Scores\n\n";
      
      axisScores.forEach(axis => {
        formattedData += `### ${axis.name}\n`;
        formattedData += `Score: ${axis.score !== null ? axis.score : 'Not available'}\n\n`;
      });
      
      return formattedData;
    } catch (e) {
      console.error('Error formatting multi-axis data:', e);
      return JSON.stringify(axisScores, null, 2);
    }
  }
  
  // As a fallback, try to extract from the result text
  const multiAxisMatch = result.match(/\[MULTI_AXIS_SCORES\]([\s\S]*?)\[END_MULTI_AXIS_SCORES\]/);
  
  if (multiAxisMatch && multiAxisMatch[1]) {
    // Clean up the data and format it
    let multiAxisData = multiAxisMatch[1].trim();
    
    try {
      // Try to parse as JSON for prettier formatting
      const parsedData = JSON.parse(multiAxisData);
      return JSON.stringify(parsedData, null, 2);
    } catch (e) {
      // If it's not valid JSON, just return the raw text
      return multiAxisData;
    }
  }
  
  return null;
}

async function createEvaluationRecords(
  evaluationTable: Table,
  applicantRecord: AirtableRecord,
  applicantFieldId: string,
  logsFieldId: string | undefined,
  linkedinDataFieldId: string | undefined,
  pdfResumeDataFieldId: string | undefined,
  multiAxisDataFieldId: string | undefined,
  // Individual axis fields
  generalPromiseFieldId: string | undefined,
  mlSkillsFieldId: string | undefined,
  softwareEngineeringFieldId: string | undefined,
  policyExperienceFieldId: string | undefined,
  aiSafetyUnderstandingFieldId: string | undefined,
  pathToImpactFieldId: string | undefined,
  researchExperienceFieldId: string | undefined,
  results: Record<string, number | string>,
  logsByField: Record<string, string>
): Promise<void> {
  Logger.info("📝 Creating evaluation record for applicant:", applicantRecord.name || applicantRecord.id);
  Logger.debug("📝 logsByField structure:", {
    fieldCount: Object.keys(logsByField).length,
    fieldIds: Object.keys(logsByField),
    sampleLogLength: Object.values(logsByField)[0]?.length || 0
  });
  
  // Log all the field IDs to debug what's being passed
  Logger.info("🔍 Field IDs received in createEvaluationRecords:", {
    logsFieldId,
    linkedinDataFieldId,
    pdfResumeDataFieldId,
    multiAxisDataFieldId,
    generalPromiseFieldId,
    mlSkillsFieldId,
    softwareEngineeringFieldId,
    policyExperienceFieldId,
    aiSafetyUnderstandingFieldId,
    pathToImpactFieldId,
    researchExperienceFieldId
  });
  
  // Create the record data
  const recordData: Record<string, any> = {
    [applicantFieldId]: [{ id: applicantRecord.id }],
  };

  // Add field results
  for (const [fieldId, value] of Object.entries(results)) {
    if (typeof value === 'number' || typeof value === 'string') {
      recordData[fieldId] = value;
    }
  }

  // Add logs if a logs field is specified
  if (logsFieldId) {
    // Strip out LinkedIn/PDF/Multi-axis blocks from the Logs field (they go to dedicated columns)
    const stripBlocks = (text: string): string => {
      return text
        // LinkedIn
        .replace(/\[LINKEDIN_DATA\][\s\S]*?\[END_LINKEDIN_DATA\]/g, '')
        // PDF resume
        .replace(/\[PDF_RESUME_DATA\][\s\S]*?\[END_PDF_RESUME_DATA\]/g, '')
        // Enrichment log
        .replace(/\[ENRICHMENT LOG\][\s\S]*?\[END ENRICHMENT LOG\]/g, '')
        // Multi-axis scores
        .replace(/\[MULTI_AXIS_SCORES\][\s\S]*?\[END_MULTI_AXIS_SCORES\]/g, '')
        .trim();
    };

    const combinedLogs = Object.entries(logsByField)
      .map(([fieldId, log]) => `## Field: ${fieldId}\n\n${stripBlocks(log)}`)
      .join('\n\n---\n\n');
    recordData[logsFieldId] = combinedLogs;
  }

  // Extract and add LinkedIn data if a LinkedIn data field is specified
  if (linkedinDataFieldId) {
    Logger.info("🔗 LinkedIn field ID exists:", linkedinDataFieldId);
    Logger.debug("🔗 Looking for LinkedIn data with linkedinDataFieldId:", linkedinDataFieldId);
    let linkedinContent = "";
    let enrichmentLogs = "";
    
    // Look for LinkedIn data and enrichment logs in any of the logs
    for (const log of Object.values(logsByField)) {
      Logger.debug("🔗 Checking log for LinkedIn data, log length:", log.length);
      
      // Check if the log contains LinkedIn markers
      if (log.includes("[LINKEDIN_DATA]")) {
        Logger.info("🔗 Found [LINKEDIN_DATA] marker in log!");
      }
      
      // Extract LinkedIn data if not already found
      if (!linkedinContent) {
        const linkedinData = extractLinkedinData(log);
        if (linkedinData) {
          Logger.info("🔗 LinkedIn data extracted successfully!", {
            dataLength: linkedinData.length,
            first100Chars: linkedinData.substring(0, 100)
          });
          linkedinContent = linkedinData;
        }
      }
      
      // Extract enrichment logs if not already found
      if (!enrichmentLogs) {
        const logs = extractEnrichmentLogs(log);
        if (logs && logs.includes("LinkedIn")) {
          Logger.debug("🔗 LinkedIn enrichment logs found!");
          enrichmentLogs = logs;
        }
      }
      
      // If we have both, break early
      if (linkedinContent && enrichmentLogs) {
        break;
      }
    }
    
    // Combine LinkedIn data with enrichment logs if available
    if (linkedinContent || enrichmentLogs) {
      let combinedData = "";
      
      if (linkedinContent) {
        combinedData += linkedinContent;
      }
      
      if (enrichmentLogs) {
        combinedData += (linkedinContent ? "\n\n---\n\n" : "") + "## Enrichment Logs\n\n" + enrichmentLogs;
      }
      
      Logger.info("🔗 Setting LinkedIn data in field:", {
        fieldId: linkedinDataFieldId,
        dataLength: combinedData.length,
        hasContent: !!linkedinContent,
        hasLogs: !!enrichmentLogs
      });
      recordData[linkedinDataFieldId] = combinedData;
      Logger.debug('📊 LinkedIn data and logs extracted and stored in specified field');
    } else {
      Logger.warn("⚠️ No LinkedIn data found in any logs");
    }
  } else {
    Logger.info("🔗 No LinkedIn field ID configured");
  }
  
  // Extract and add PDF resume data if a PDF resume data field is specified
  if (pdfResumeDataFieldId) {
    Logger.info("📑 PDF field ID exists:", pdfResumeDataFieldId);
    Logger.debug("📑 Looking for PDF resume data with pdfResumeDataFieldId:", pdfResumeDataFieldId);
    let pdfContent = "";
    let enrichmentLogs = "";
    
    // Look for PDF resume data and enrichment logs in any of the logs
    for (const log of Object.values(logsByField)) {
      Logger.debug("📑 Checking log for PDF resume data, log length:", log.length);
      
      // Check if the log contains PDF markers
      if (log.includes("[PDF_RESUME_DATA]")) {
        Logger.info("📑 Found [PDF_RESUME_DATA] marker in log!");
      }
      
      // Extract PDF data if not already found
      if (!pdfContent) {
        const pdfResumeData = extractPdfResumeData(log);
        if (pdfResumeData) {
          Logger.info("📑 PDF resume data extracted successfully!", {
            dataLength: pdfResumeData.length,
            first100Chars: pdfResumeData.substring(0, 100)
          });
          pdfContent = pdfResumeData;
        }
      }
      
      // Extract enrichment logs if not already found (look for PDF-related logs)
      if (!enrichmentLogs) {
        const logs = extractEnrichmentLogs(log);
        if (logs && (logs.includes("PDF") || logs.includes("resume"))) {
          Logger.debug("📑 PDF enrichment logs found!");
          enrichmentLogs = logs;
        }
      }
      
      // If we have both, break early
      if (pdfContent && enrichmentLogs) {
        break;
      }
    }
    
    // Combine PDF data with enrichment logs if available
    if (pdfContent || enrichmentLogs) {
      let combinedData = "";
      
      if (pdfContent) {
        combinedData += pdfContent;
      }
      
      if (enrichmentLogs) {
        combinedData += (pdfContent ? "\n\n---\n\n" : "") + "## Enrichment Logs\n\n" + enrichmentLogs;
      }
      
      Logger.info("📑 Setting PDF data in field:", {
        fieldId: pdfResumeDataFieldId,
        dataLength: combinedData.length,
        hasContent: !!pdfContent,
        hasLogs: !!enrichmentLogs
      });
      recordData[pdfResumeDataFieldId] = combinedData;
      Logger.debug('📄 PDF resume data and logs extracted and stored in specified field');
    } else {
      Logger.warn("⚠️ No PDF resume data found in any logs");
    }
  } else {
    Logger.info("📑 No PDF field ID configured");
  }
  
  // Extract and add multi-axis data and individual scores
  // Check if multi_axis_scores exists in the results object
  if (results.multi_axis_scores && Array.isArray(results.multi_axis_scores)) {
    Logger.debug("📊 Multi-axis scores found in results object!");
    const multiAxisScores = results.multi_axis_scores as Array<{name: string, score: number | null}>;
    Logger.debug("📋 Multi-axis field IDs:", {
      generalPromiseFieldId,
      mlSkillsFieldId,
      softwareEngineeringFieldId,
      policyExperienceFieldId,
      aiSafetyUnderstandingFieldId,
      pathToImpactFieldId,
      researchExperienceFieldId
    });
    Logger.debug("📋 Axis scores array:", multiAxisScores);
    // Add individual axis scores to their respective fields
    if (multiAxisScores.length > 0) {
      Logger.debug("📊 Processing individual axis scores");
      
      // Process each axis score and add to the corresponding field if defined
      multiAxisScores.forEach(axisScore => {
        const axisName = axisScore.name;
        const score = axisScore.score;
        
        if (score !== null) {
          // General Promise
          if (generalPromiseFieldId && axisName === "General Promise") {
            Logger.debug(`📊 Adding General Promise score (${score}) to field: ${generalPromiseFieldId}`);
            recordData[generalPromiseFieldId] = score;
          }
          
          // ML Skills
          else if (mlSkillsFieldId && axisName === "ML Skills") {
            Logger.debug(`📊 Adding ML Skills score (${score}) to field: ${mlSkillsFieldId}`);
            recordData[mlSkillsFieldId] = score;
          }
          
          // Software Engineering Skills
          else if (softwareEngineeringFieldId && axisName === "Software Engineering Skills") {
            Logger.debug(`📊 Adding Software Engineering score (${score}) to field: ${softwareEngineeringFieldId}`);
            recordData[softwareEngineeringFieldId] = score;
          }
          
          // Policy Experience
          else if (policyExperienceFieldId && axisName === "Policy Experience") {
            Logger.debug(`📊 Adding Policy Experience score (${score}) to field: ${policyExperienceFieldId}`);
            recordData[policyExperienceFieldId] = score;
          }
          
          // Understanding of AI Safety
          else if (aiSafetyUnderstandingFieldId && axisName === "Understanding of AI Safety") {
            Logger.debug(`📊 Adding AI Safety Understanding score (${score}) to field: ${aiSafetyUnderstandingFieldId}`);
            recordData[aiSafetyUnderstandingFieldId] = score;
          }
          
          // Path to Impact
          else if (pathToImpactFieldId && axisName === "Path to Impact") {
            Logger.debug(`📊 Adding Path to Impact score (${score}) to field: ${pathToImpactFieldId}`);
            recordData[pathToImpactFieldId] = score;
          }
          
          // Research Experience
          else if (researchExperienceFieldId && axisName === "Research Experience") {
            Logger.debug(`📊 Adding Research Experience score (${score}) to field: ${researchExperienceFieldId}`);
            recordData[researchExperienceFieldId] = score;
          }
        }
      });
    }
    
    // Add the formatted multi-axis data to the multi-axis data field if specified
    if (multiAxisDataFieldId) {
      Logger.debug("📊 Looking for multi-axis data with multiAxisDataFieldId:", multiAxisDataFieldId);
      const multiAxisData = extractMultiAxisData("", multiAxisScores);
      
      if (multiAxisData) {
        Logger.debug("📊 Formatting multi-axis data for field:", multiAxisDataFieldId);
        Logger.debug("📊 Multi-axis data snippet:", multiAxisData.substring(0, 100) + "...");
        recordData[multiAxisDataFieldId] = multiAxisData;
        Logger.debug('📊 Multi-axis data extracted and stored in specified field');
      }
    }
  } 
  // Try to find multi-axis data in logs as fallback
  else if (multiAxisDataFieldId) {
    Logger.debug("📊 No multi_axis_scores in results, checking logs for multi-axis data");
    // Look for multi-axis data in any of the logs as fallback
    for (const log of Object.values(logsByField)) {
      Logger.debug("📊 Checking log for multi-axis data, log length:", log.length);
      const multiAxisData = extractMultiAxisData(log);
      if (multiAxisData) {
        Logger.debug("📊 Multi-axis data found in log! Setting in field:", multiAxisDataFieldId);
        Logger.debug("📊 Multi-axis data snippet:", multiAxisData.substring(0, 100) + "...");
        recordData[multiAxisDataFieldId] = multiAxisData;
        Logger.debug('📊 Multi-axis data extracted and stored in specified field');
        break;
      }
    }
    
    // If we get here and haven't found data, log it
    if (!recordData[multiAxisDataFieldId]) {
      Logger.warn("⚠️ No multi-axis data found in results or logs");
    }
  }

  Logger.debug('📋 Enrichment logs structure:', logsByField);
  // Log final record data for debugging which fields will be written
  Logger.info('📤 Final recordData to write:', {
    fieldIds: Object.keys(recordData),
    hasLinkedinData: linkedinDataFieldId ? linkedinDataFieldId in recordData : 'N/A',
    hasPdfData: pdfResumeDataFieldId ? pdfResumeDataFieldId in recordData : 'N/A',
    hasMultiAxisData: multiAxisDataFieldId ? multiAxisDataFieldId in recordData : 'N/A'
  });
  Logger.debug('📤 Full recordData:', recordData);
  // Create the record
  await evaluationTable.createRecordAsync(recordData);
}

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