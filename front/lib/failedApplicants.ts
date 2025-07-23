/**
 * Failed applicant tracking for retry functionality
 */

import { globalConfig } from '@airtable/blocks';
import type { Record as AirtableRecord } from '@airtable/blocks/models';
import { Logger } from './logger';

export interface FailedApplicant {
  recordId: string;
  reason: string;
  timestamp: number;
  batchNumber: number;
  preset: string;
  applicantName?: string; // For display purposes
  applicantData?: Record<string, string>; // Store key applicant fields for retry
}

/**
 * Get all failed applicants from global config
 */
export const getFailedApplicants = (): FailedApplicant[] => {
  const failed = globalConfig.get('failedApplicants') as FailedApplicant[] | null;
  return failed || [];
};

/**
 * Process a single field for applicant data extraction
 */
const processApplicantField = (
  applicant: AirtableRecord,
  field: { fieldId: string; questionName?: string },
  currentName: string
): { fieldData: [string, string] | null; updatedName: string } => {
  try {
    const value = applicant.getCellValueAsString(field.fieldId) || '';
    const key = field.questionName || field.fieldId;

    // Update name if we haven't found a good one yet
    let updatedName = currentName;
    if ((!currentName || currentName === applicant.id) && value?.trim()) {
      updatedName = value.length > 50 ? `${value.substring(0, 47)}...` : value;
    }

    return { fieldData: [key, value], updatedName };
  } catch (error) {
    return { fieldData: null, updatedName: currentName };
  }
};

/**
 * Extract applicant data and name for failed applicant tracking
 */
const extractApplicantData = (
  applicant: AirtableRecord,
  applicantFields?: Array<{ fieldId: string; questionName?: string }>
): { applicantName: string; applicantData: Record<string, string> } => {
  let applicantName = applicant.id; // Fallback to ID
  const applicantData: Record<string, string> = {};

  if (!applicantFields) {
    return { applicantName, applicantData };
  }

  for (const field of applicantFields) {
    const { fieldData, updatedName } = processApplicantField(
      applicant,
      field,
      applicantName
    );
    applicantName = updatedName;

    if (fieldData) {
      applicantData[fieldData[0]] = fieldData[1];
    }
  }

  return { applicantName, applicantData };
};

/**
 * Convert applicant record to FailedApplicant entry
 */
const createFailedApplicantEntry = (
  applicant: AirtableRecord,
  reason: string,
  batchNumber: number,
  presetName: string,
  applicantFields?: Array<{ fieldId: string; questionName?: string }>
): FailedApplicant => {
  const { applicantName, applicantData } = extractApplicantData(
    applicant,
    applicantFields
  );

  return {
    recordId: applicant.id,
    reason,
    timestamp: Date.now(),
    batchNumber,
    preset: presetName,
    applicantName,
    applicantData,
  };
};

/**
 * Add failed applicants to global config with enhanced data
 */
export const addFailedApplicants = async (
  applicants: AirtableRecord[],
  reason: string,
  batchNumber: number,
  presetName: string,
  applicantFields?: Array<{ fieldId: string; questionName?: string }>
): Promise<void> => {
  const existing = getFailedApplicants();

  const newFailed: FailedApplicant[] = applicants.map((applicant) =>
    createFailedApplicantEntry(
      applicant,
      reason,
      batchNumber,
      presetName,
      applicantFields
    )
  );

  const updated = [...existing, ...newFailed];

  await globalConfig.setAsync('failedApplicants', updated as any);

  Logger.info(
    `📝 Added ${newFailed.length} failed applicants to retry list. Total: ${updated.length}`
  );
};

/**
 * Clear failed applicants (after successful retry or manual clear)
 */
export const clearFailedApplicants = async (): Promise<void> => {
  await globalConfig.setAsync('failedApplicants', []);
  Logger.info('🧹 Cleared failed applicants list');
};

/**
 * Remove specific failed applicants (after successful retry)
 */
export const removeFailedApplicants = async (recordIds: string[]): Promise<void> => {
  const existing = getFailedApplicants();
  const filtered = existing.filter((failed) => !recordIds.includes(failed.recordId));

  await globalConfig.setAsync('failedApplicants', filtered as any);

  Logger.info(
    `✅ Removed ${recordIds.length} successfully retried applicants from failed list`
  );
};

/**
 * Get failed applicants count for display
 */
export const getFailedApplicantsCount = (): number => {
  return getFailedApplicants().length;
};
