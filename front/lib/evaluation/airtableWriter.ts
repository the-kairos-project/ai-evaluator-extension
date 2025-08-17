import type { Record as AirtableRecord, Table } from '@airtable/blocks/models';
import { Logger } from '../logger';
import { extractLinkedinData, extractEnrichmentLogs, extractPdfResumeData, extractMultiAxisData } from './extractors';

/**
 * Extracts applicant name from record for display purposes
 * Tries primary field first, then any field containing "name", finally falls back to record ID
 */
export const getApplicantName = (applicant: AirtableRecord): string => {
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
export const setApplicantNameInResult = (
  result: Record<string, unknown>,
  applicant: AirtableRecord,
  evaluationTable?: Table
): void => {
  if (!evaluationTable?.primaryField) return;

  const applicantName = getApplicantName(applicant);
  result[evaluationTable.primaryField.id] = applicantName;
};

/**
 * Create evaluation records in Airtable
 */
export async function createEvaluationRecords(
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
    // We will copy the full logs (including enrichment blocks) into the Logs field
    // while still extracting LinkedIn/PDF/Multi-axis into their dedicated columns.
    const combinedLogsFull = Object.entries(logsByField)
      .map(([fieldId, log]) => `## Field: ${fieldId}\n\n${log}`)
      .join('\n\n---\n\n');

    recordData[logsFieldId] = combinedLogsFull;
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
  
  Logger.info('📋 Enrichment logs structure:', logsByField);
  // Log final record data for debugging which fields will be written
  // Additional debug: log snippets of logsByField to help debug extraction
  try {
    const snippets = Object.entries(logsByField).map(([k, v]) => ({ key: k, len: v?.length || 0, snippet: (v || '').substring(0, 200) }));
    Logger.info('🔎 logsByField snippets for extraction debugging:', snippets);
  } catch (e) {
    Logger.info('🔎 Failed to build logsByField snippets', e);
  }
  Logger.info('📤 Final recordData to write:', {
    fieldIds: Object.keys(recordData),
    hasLinkedinData: linkedinDataFieldId ? linkedinDataFieldId in recordData : 'N/A',
    hasPdfData: pdfResumeDataFieldId ? pdfResumeDataFieldId in recordData : 'N/A',
    hasMultiAxisData: multiAxisDataFieldId ? multiAxisDataFieldId in recordData : 'N/A'
  });
  // Also log a JSON snippet of the full recordData to ensure visibility in DevTools
  try {
    const json = JSON.stringify(recordData, null, 2);
    Logger.info('📤 Full recordData JSON snippet (truncated 10k chars):', json.substring(0, 10000));
  } catch (e) {
    Logger.info('📤 Full recordData (non-serializable), keys:', Object.keys(recordData));
  }

  // Additionally log explicit enrichment field contents if present for easier visibility
  try {
    if (linkedinDataFieldId && recordData[linkedinDataFieldId]) {
      Logger.info('🔗 LinkedIn field content snippet:', String(recordData[linkedinDataFieldId]).substring(0, 2000));
    }
    if (pdfResumeDataFieldId && recordData[pdfResumeDataFieldId]) {
      Logger.info('📄 PDF resume field content snippet:', String(recordData[pdfResumeDataFieldId]).substring(0, 2000));
    }
    if (multiAxisDataFieldId && recordData[multiAxisDataFieldId]) {
      Logger.info('📊 Multi-axis field content snippet:', String(recordData[multiAxisDataFieldId]).substring(0, 2000));
    }
  } catch (e) {
    Logger.info('🔎 Error logging enrichment field snippets', e);
  }
  // Create the record
  await evaluationTable.createRecordAsync(recordData);
}

export default {};


