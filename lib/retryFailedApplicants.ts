/**
 * Retry functionality for failed applicants
 */

import type { Record as AirtableRecord, Table } from '@airtable/blocks/models';
import pRetry from 'p-retry';
import { type SetProgress, evaluateApplicants } from './evaluateApplicants';
import { type FailedApplicant, removeFailedApplicants } from './failedApplicants';
import type { Preset } from './preset';

/**
 * Retry failed applicants by fetching their records and re-processing
 */
export const retryFailedApplicants = async (
  failedApplicants: FailedApplicant[],
  preset: Preset,
  applicantTable: Table,
  evaluationTable: Table,
  setProgress: SetProgress,
  setResult: (result: string) => void
): Promise<{ successes: number; failures: number; newFailures: FailedApplicant[] }> => {
  if (failedApplicants.length === 0) {
    return { successes: 0, failures: 0, newFailures: [] };
  }

  console.log(`🔄 Starting retry for ${failedApplicants.length} failed applicants`);
  setResult('Fetching failed applicant records for retry...');

  // Fetch actual records from Airtable using the stored record IDs
  const recordIds = failedApplicants.map((f) => f.recordId);
  const records: AirtableRecord[] = [];
  const notFoundIds: string[] = [];

  // Fetch all records from the table and filter by IDs
  // This is necessary because Airtable blocks don't have getRecordByIdIfExists
  const view = applicantTable.views[0]; // Use first view
  const allRecords = await view.selectRecordsAsync();

  for (const recordId of recordIds) {
    const record = allRecords.records.find((r) => r.id === recordId);
    if (record) {
      records.push(record);
    } else {
      notFoundIds.push(recordId);
      console.warn(`⚠️ Record ${recordId} not found in table, may have been deleted`);
    }
  }

  // Clean up the record selection
  allRecords.unloadData();

  if (notFoundIds.length > 0) {
    setResult(
      `Warning: ${notFoundIds.length} applicants not found (may have been deleted)`
    );
    // Remove not-found applicants from failed list
    await removeFailedApplicants(notFoundIds);
  }

  if (records.length === 0) {
    setResult('No valid records found to retry');
    return { successes: 0, failures: 0, newFailures: [] };
  }

  setResult(`Retrying ${records.length} failed applicants...`);

  // Use single-batch processing for retry (simpler approach)
  const evaluationPromises = evaluateApplicants(records, preset, setProgress);

  if (evaluationPromises.length === 0) {
    setResult('No evaluation promises generated for retry');
    return { successes: 0, failures: 0, newFailures: [] };
  }

  const results = await Promise.allSettled(
    evaluationPromises.map(async (evaluationPromise, index) => {
      const record = records[index];
      const startTime = Date.now();

      try {
        setResult(`Retrying applicant ${index + 1} of ${records.length}...`);

        // Add timeout for retry as well (90 seconds per applicant)
        const RETRY_TIMEOUT = 90 * 1000;
        const evaluation = await Promise.race([
          evaluationPromise,
          new Promise<Record<string, unknown>>((_, reject) =>
            setTimeout(
              () => reject(new Error(`Retry timeout after ${RETRY_TIMEOUT / 1000}s`)),
              RETRY_TIMEOUT
            )
          ),
        ]);

        // Save to Airtable
        await pRetry(() => evaluationTable.createRecordAsync(evaluation));

        const totalTime = Date.now() - startTime;
        console.log(`✅ Successfully retried applicant ${record.id} in ${totalTime}ms`);

        return { success: true, recordId: record.id, totalTime };
      } catch (error) {
        const totalTime = Date.now() - startTime;
        console.error(
          `❌ Failed to retry applicant ${record.id} after ${totalTime}ms:`,
          error
        );

        return { success: false, recordId: record.id, error, totalTime };
      }
    })
  );

  // Count successes and failures
  const successes = results.filter(
    (r) => r.status === 'fulfilled' && r.value?.success
  ).length;
  const failures = results.length - successes;

  // Remove successfully retried applicants from failed list
  const successfulIds = results
    .filter((r) => r.status === 'fulfilled' && r.value?.success)
    .map((r) => (r as any).value.recordId);

  if (successfulIds.length > 0) {
    await removeFailedApplicants(successfulIds);
  }

  // Create new failed applicant entries for those that failed again
  const newFailures: FailedApplicant[] = results
    .filter((r) => r.status === 'fulfilled' && !r.value?.success)
    .map((r) => {
      const recordId = (r as any).value.recordId;
      const originalFailed = failedApplicants.find((f) => f.recordId === recordId);

      return {
        recordId,
        reason: `Retry failed: ${(r as any).value.error?.message || 'Unknown error'}`,
        timestamp: Date.now(),
        batchNumber: -1, // Special marker for retry failures
        preset: preset.name,
        applicantName: originalFailed?.applicantName,
        applicantData: originalFailed?.applicantData,
      };
    });

  console.log(
    `✅ Retry complete: ${successes} successes, ${failures} failures out of ${records.length} attempted`
  );

  return { successes, failures, newFailures };
};
