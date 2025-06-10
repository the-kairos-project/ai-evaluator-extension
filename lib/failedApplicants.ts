/**
 * Failed applicant tracking for retry functionality
 */

import { globalConfig } from '@airtable/blocks';
import type { Record as AirtableRecord } from '@airtable/blocks/models';

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
 * Add failed applicants to global config with enhanced data
 */
export const addFailedApplicants = async (
  applicants: AirtableRecord[],
  reason: string,
  batchNumber: number,
  presetName: string,
  applicantFields?: Array<{ fieldId: string; questionName?: string }> // For extracting applicant data
): Promise<void> => {
  const existing = getFailedApplicants();

  const newFailed: FailedApplicant[] = applicants.map((applicant) => {
    // Extract applicant name and key data for display
    let applicantName = applicant.id; // Fallback to ID
    const applicantData: Record<string, string> = {};

    if (applicantFields) {
      for (const field of applicantFields) {
        try {
          const value = applicant.getCellValueAsString(field.fieldId) || '';
          const key = field.questionName || field.fieldId;
          applicantData[key] = value;

          // Use first non-empty field as the display name
          if (!applicantName || applicantName === applicant.id) {
            if (value?.trim()) {
              applicantName =
                value.length > 50 ? `${value.substring(0, 47)}...` : value;
            }
          }
        } catch (error) {
          // Skip fields that can't be read
        }
      }
    }

    return {
      recordId: applicant.id,
      reason,
      timestamp: Date.now(),
      batchNumber,
      preset: presetName,
      applicantName,
      applicantData,
    };
  });

  const updated = [...existing, ...newFailed];

  await globalConfig.setAsync('failedApplicants', updated as any);

  console.log(
    `📝 Added ${newFailed.length} failed applicants to retry list. Total: ${updated.length}`
  );
};

/**
 * Clear failed applicants (after successful retry or manual clear)
 */
export const clearFailedApplicants = async (): Promise<void> => {
  await globalConfig.setAsync('failedApplicants', []);
  console.log('🧹 Cleared failed applicants list');
};

/**
 * Remove specific failed applicants (after successful retry)
 */
export const removeFailedApplicants = async (recordIds: string[]): Promise<void> => {
  const existing = getFailedApplicants();
  const filtered = existing.filter((failed) => !recordIds.includes(failed.recordId));

  await globalConfig.setAsync('failedApplicants', filtered as any);

  console.log(
    `✅ Removed ${recordIds.length} successfully retried applicants from failed list`
  );
};

/**
 * Get failed applicants count for display
 */
export const getFailedApplicantsCount = (): number => {
  return getFailedApplicants().length;
};
