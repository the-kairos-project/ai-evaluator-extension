import {
  Button,
  FieldPicker,
  FieldPickerSynced,
  FormField,
  Input,
  ProgressBar,
  Select,
  TablePickerSynced,
  Text,
  ViewPickerSynced,
  useBase,
} from '@airtable/blocks/ui';
import React, { useState, useMemo } from 'react';
import { Logger } from '../lib/logger';

import { globalConfig } from '@airtable/blocks';
import {
  type Record as AirtableRecord,
  type Field,
  FieldType,
  type Table,
} from '@airtable/blocks/models';
import pRetry from 'p-retry';
import { estimateBatchCost, formatCostEstimate } from '../lib/estimation';
import { type SetProgress, evaluateApplicants } from '../lib/evaluateApplicants';
import { isServerModeEnabled } from '../lib/getChatCompletion/server';
import {
  addFailedApplicants,
  clearFailedApplicants,
  getFailedApplicants,
  getFailedApplicantsCount,
} from '../lib/failedApplicants';
import { PROVIDER_ICONS, formatModelName, DEFAULT_OPENAI_MODEL } from '../lib/models/config';
import { type Preset, upsertPreset, useSelectedPreset } from '../lib/preset';
import { retryFailedApplicants } from '../lib/retryFailedApplicants';
import { FailedApplicantsModal } from './components/FailedApplicantsModal';
import { FormFieldWithTooltip, useGuidedMode } from './components/helpSystem';

// Helper function to build dependency map
const buildDependencyMap = (preset: Preset): Map<string, string[]> => {
  const dependencyMap = new Map<string, string[]>();

  for (const { fieldId, dependsOnInputField } of preset.evaluationFields) {
    if (dependsOnInputField) {
      if (!dependencyMap.has(dependsOnInputField)) {
        dependencyMap.set(dependsOnInputField, []);
      }
      dependencyMap.get(dependsOnInputField).push(fieldId);
    }
  }

  return dependencyMap;
};

// Helper function to check if an applicant should be processed
const shouldProcessApplicant = (
  applicant: AirtableRecord,
  dependencyFields: string[]
): boolean => {
  for (const inputFieldId of dependencyFields) {
    const value = applicant.getCellValueAsString(inputFieldId);
    if (value && value.trim() !== '') {
      return true;
    }
  }
  return false;
};

// Fast precheck function to filter out applicants that don't need processing
const quickPrecheck = async (
  applicants: AirtableRecord[],
  preset: Preset,
  setProgress: SetProgress
) => {
  // Create a dependency map for quick lookups
  const dependencyMap = buildDependencyMap(preset);

  // If no dependencies, process all applicants
  if (dependencyMap.size === 0) {
    return {
      applicantsToProcess: applicants,
      skippedApplicants: [],
    };
  }

  // Fast check on each applicant
  const applicantsToProcess = [];
  const skippedApplicants = [];
  const dependencyFields = Array.from(dependencyMap.keys());

  // Process in small batches to show progress
  const batchSize = 100;
  for (let i = 0; i < applicants.length; i += batchSize) {
    const batch = applicants.slice(i, i + batchSize);

    for (const applicant of batch) {
      if (shouldProcessApplicant(applicant, dependencyFields)) {
        applicantsToProcess.push(applicant);
      } else {
        skippedApplicants.push(applicant);
      }
    }

    // Update progress to show the precheck is working
    setProgress(() => (i / applicants.length) * 0.1); // Use 10% of progress bar for precheck
  }

  return {
    applicantsToProcess,
    skippedApplicants,
  };
};

// Helper function to get current model from settings
const getCurrentModel = (): string => {
  const selectedProvider = (globalConfig.get('selectedModel') as string) || 'openai';
  if (selectedProvider === 'openai') {
    return (globalConfig.get('openAiModel') as string) || DEFAULT_OPENAI_MODEL;
  }
  return (globalConfig.get('anthropicModel') as string) || 'claude-3-5-sonnet-20241022';
};

const renderPreviewText = (
  numberOfApplicants: number,
  numberOfEvaluationCriteria: number,
  applicantsData?: Record<string, string>[],
  evaluationFields?: Array<{ criteria: string }>
) => {
  const numberOfItems = numberOfApplicants * numberOfEvaluationCriteria;

  // Try to provide realistic cost estimate if we have the data
  if (applicantsData && evaluationFields && applicantsData.length > 0) {
    try {
      const currentModel = getCurrentModel();
      const estimate = estimateBatchCost(
        applicantsData,
        evaluationFields,
        currentModel
      );
      const costText = formatCostEstimate(estimate);

      return `Found ${numberOfApplicants} records, and ${numberOfEvaluationCriteria} evaluation criteria. ${costText}. To cancel, please close the entire browser tab.`;
    } catch (error) {
      Logger.warn('Cost estimation failed, using fallback:', error);
    }
  }

  // Fallback to old estimation if new system fails
  const costEstimateGbp = (numberOfItems * 0.011).toFixed(2);
  return `Found ${numberOfApplicants} records, and ${numberOfEvaluationCriteria} evaluation criteria for a total of ${numberOfItems} items to process. Estimated cost: £${costEstimateGbp} (rough estimate). To cancel, please close the entire browser tab.`;
};

// Helper function to format processing rate
export const formatProcessingRate = (
  processedCount: number,
  startTime: number | null
): string => {
  if (!startTime || processedCount === 0) return '';
  
  const elapsedMs = Date.now() - startTime;
  const elapsedMinutes = elapsedMs / (1000 * 60);
  
  if (elapsedMinutes < 0.5) {
    // Too early to calculate meaningful rate
    return '';
  }
  
  const appsPerMinute = processedCount / elapsedMinutes;
  
  if (appsPerMinute >= 2) {
    return ` (${appsPerMinute.toFixed(1)} apps/min)`;
  } else {
    // Use apps per hour for slower rates
    const appsPerHour = appsPerMinute * 60;
    return ` (${appsPerHour.toFixed(0)} apps/hour)`;
  }
};

export const MainPage = () => {
  const preset = useSelectedPreset();
  const showGuidedHelp = useGuidedMode();

  const base = useBase();
  const applicantTable = base.getTableByIdIfExists(preset.applicantTableId);
  const evaluationTable = base.getTableByIdIfExists(preset.evaluationTableId);

  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0); // between 0.0 and 1.0
  const [result, setResult] = useState<string>(null);
  const [failedCount, setFailedCount] = useState(getFailedApplicantsCount());
  const [showFailedModal, setShowFailedModal] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [processingStartTime, setProcessingStartTime] = useState<number | null>(null);
  /**
   * Process applicants in batches to prevent browser overload
   * Works with the existing LLM API concurrency limits
   */
  async function processBatchedApplicants(
    applicantsToProcess: AirtableRecord[],
    preset: Preset,
    evaluationTable: Table,
    setProgress: (updater: (prev: number) => number) => void,
    setResult: (result: string) => void,
    startTime: number | null
  ): Promise<{ successes: number; failures: number }> {
    // Dynamic batch sizing based on field count to optimize concurrency
    const fieldCount = preset.evaluationFields.length;
    const currentConcurrency = (
      await import('../lib/concurrency/config')
    ).getCurrentConcurrency();
    const BATCH_SIZE = Math.max(1, Math.floor(currentConcurrency / fieldCount));

    Logger.debug(
      `Processing with batch size of ${BATCH_SIZE} applicants per batch ` +
        `(${fieldCount} fields each, optimized for ${currentConcurrency} concurrent API calls)`
    );

    let totalSuccesses = 0;
    let totalFailures = 0;
    let processedCount = 0;

    // Process in batches to manage memory
    Logger.debug(
      `🔄 Starting batch processing loop. Total applicants: ${applicantsToProcess.length}, Batch size: ${BATCH_SIZE}`
    );

    for (
      let batchStart = 0;
      batchStart < applicantsToProcess.length;
      batchStart += BATCH_SIZE
    ) {
      Logger.debug(
        `🔄 === STARTING BATCH ITERATION: batchStart=${batchStart}, BATCH_SIZE=${BATCH_SIZE} ===`
      );

      // Extract the current batch
      const currentBatch = applicantsToProcess.slice(
        batchStart,
        Math.min(batchStart + BATCH_SIZE, applicantsToProcess.length)
      );

      const batchNumber = Math.floor(batchStart / BATCH_SIZE) + 1;
      const totalBatches = Math.ceil(applicantsToProcess.length / BATCH_SIZE);

      Logger.debug(
        `📦 Batch ${batchNumber}/${totalBatches}: Processing ${currentBatch.length} applicants (${batchStart + 1}-${Math.min(batchStart + BATCH_SIZE, applicantsToProcess.length)})`
      );

      setResult(
        `Processing batch ${batchNumber} of ${totalBatches} ` +
          `(applicants ${batchStart + 1}-${Math.min(
            batchStart + BATCH_SIZE,
            applicantsToProcess.length
          )} ` +
          `of ${applicantsToProcess.length})${formatProcessingRate(processedCount, startTime)}`
      );

      // Get evaluation promises for this batch only
      Logger.debug(
        `🔨 Generating evaluation promises for batch ${batchNumber} with ${currentBatch.length} applicants...`
      );
      const batchEvaluationPromises = evaluateApplicants(
        currentBatch,
        preset,
        (updater) => {
          // Adjust progress to account for batching
          const batchProgress = updater(0);
          const batchContribution =
            batchProgress * (currentBatch.length / applicantsToProcess.length);
          const overallProgressOffset = batchStart / applicantsToProcess.length;

          setProgress(() => 0.1 + 0.9 * (overallProgressOffset + batchContribution));
        },
        evaluationTable // Pass the evaluation table for name field population
      );
      Logger.debug(
        `✅ Generated ${batchEvaluationPromises.length} evaluation promises for batch ${batchNumber}`
      );

      if (batchEvaluationPromises.length === 0) {
        Logger.debug(
          `⚠️ WARNING: No evaluation promises generated for batch ${batchNumber}. Skipping batch.`
        );
        continue;
      }

      // Process each evaluation and write to Airtable
      Logger.debug(
        `🔄 Starting Promise.allSettled for batch ${batchNumber} with ${batchEvaluationPromises.length} promises`
      );
      Logger.debug(`📋 Expected applicants in this batch: ${currentBatch.length}`);
      Logger.debug(`🎯 Expected promises: ${batchEvaluationPromises.length}`);

      if (batchEvaluationPromises.length !== currentBatch.length) {
        Logger.warn(
          `⚠️ MISMATCH: Expected ${currentBatch.length} promises but got ${batchEvaluationPromises.length}`
        );
      }

      // Track promise completion in real-time
      let completedPromises = 0;
      const startAllSettled = Date.now();

      // Add batch-level timeout (5 minutes per batch)
      const BATCH_TIMEOUT = 5 * 60 * 1000; // 5 minutes

      const batchPromise = Promise.allSettled(
        batchEvaluationPromises.map(async (evaluationPromise, index) => {
          const applicantNumber = batchStart + index + 1;
          const startTime = Date.now();

          Logger.debug(
            `🚀 Starting processing of applicant ${applicantNumber} (index ${index} in batch ${batchNumber})`
          );

          try {
            setResult(
              `Processing batch ${batchNumber} of ${totalBatches} - ` +
                `Evaluating applicant ${applicantNumber} of ${applicantsToProcess.length}...${formatProcessingRate(processedCount + completedPromises, startTime)}`
            );

            Logger.debug(
              `⏳ Awaiting evaluation promise for applicant ${applicantNumber}...`
            );

            const evaluation = await evaluationPromise;

            Logger.debug(
              `✅ Evaluation promise resolved for applicant ${applicantNumber}`
            );

            // Check if evaluation contains applicant ID before logging
            const applicantId = evaluation[preset.evaluationApplicantField]?.[0]?.id;
            const evaluationTime = Date.now() - startTime;

            Logger.debug(
              `✅ Evaluated applicant ${applicantNumber} (ID: ${
                applicantId || 'unknown'
              }) in ${evaluationTime}ms, uploading to Airtable...`
            );

            setResult(
              `Processing batch ${batchNumber} of ${totalBatches} - ` +
                `Saving applicant ${applicantNumber} to Airtable...${formatProcessingRate(processedCount + completedPromises, startTime)}`
            );

            // Write to Airtable with retry
            Logger.debug(
              `💾 Starting Airtable save for applicant ${applicantNumber}...`
            );
            const airtableStartTime = Date.now();

            try {
              await pRetry(
                () => {
                  Logger.debug(
                    `🔄 Attempting Airtable createRecord for applicant ${applicantNumber}...`
                  );
                  Logger.debug('📤 Record data to write to Airtable:', evaluation);
                  return evaluationTable.createRecordAsync(evaluation);
                },
                {
                  retries: 3,
                  factor: 2,
                  minTimeout: 1000,
                  onFailedAttempt: (error) => {
                    Logger.warn(
                      `⚠️ Airtable save retry ${error.attemptNumber} for applicant ${applicantNumber}: ${error.message}`
                    );
                  },
                }
              );

              const airtableTime = Date.now() - airtableStartTime;
              Logger.debug(
                `✅ Airtable save successful for applicant ${applicantNumber} in ${airtableTime}ms`
              );
            } catch (airtableError) {
              const airtableTime = Date.now() - airtableStartTime;
              Logger.error(
                `❌ Airtable save failed for applicant ${applicantNumber} after ${airtableTime}ms:`,
                airtableError
              );
              throw airtableError;
            }

            const airtableTime = Date.now() - airtableStartTime;

            const totalTime = Date.now() - startTime;
            Logger.debug(
              `✅ Saved applicant ${applicantNumber} to Airtable in ${airtableTime}ms ` +
                `(total: ${totalTime}ms)`
            );

            Logger.debug(`🎯 Returning success result for applicant ${applicantNumber}`);
            completedPromises++;
            Logger.debug(
              `📊 Progress: ${completedPromises}/${batchEvaluationPromises.length} promises completed`
            );
            return {
              success: true,
              applicantNumber,
              evaluationTime,
              airtableTime,
              totalTime,
            };
          } catch (error) {
            const totalTime = Date.now() - startTime;
            Logger.error(
              `❌ Failed to process applicant ${applicantNumber} after ${totalTime}ms:`,
              error
            );
            Logger.debug(`🎯 Returning error result for applicant ${applicantNumber}`);
            completedPromises++;
            Logger.debug(
              `📊 Progress: ${completedPromises}/${batchEvaluationPromises.length} promises completed (with error)`
            );
            return { success: false, error, applicantNumber, totalTime };
          }
        })
      );

      // Race the batch promise against the batch timeout
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(
          () =>
            reject(
              new Error(`Batch ${batchNumber} timeout after ${BATCH_TIMEOUT / 1000}s`)
            ),
          BATCH_TIMEOUT
        )
      );

      let batchResults: any;
      let timedOut = false;

      try {
        Logger.debug(
          `⏰ Starting batch ${batchNumber} with ${BATCH_TIMEOUT / 1000}s timeout...`
        );
        batchResults = await Promise.race([batchPromise, timeoutPromise]);
        Logger.debug(`✅ Batch ${batchNumber} completed successfully within timeout`);
      } catch (error) {
        if (error.message.includes('timeout')) {
          Logger.error(
            `⏰ Batch ${batchNumber} timed out! Handling partial results...`
          );
          timedOut = true;

          // Get whatever results we have so far (some promises may have completed)
          const partialResults = await Promise.allSettled(
            batchEvaluationPromises.map(() =>
              Promise.resolve({
                success: false,
                error: 'Batch timeout',
                applicantNumber: -1,
                totalTime: BATCH_TIMEOUT,
              })
            )
          );
          batchResults = partialResults;

          // Track the hanging applicants for retry
          const hangingApplicants = currentBatch.filter((_, index) => {
            // If we have fewer results than expected, these applicants are hanging
            return index >= completedPromises;
          });

          if (hangingApplicants.length > 0) {
            await addFailedApplicants(
              hangingApplicants,
              `Batch timeout - ${hangingApplicants.length} applicants didn't complete in ${BATCH_TIMEOUT / 1000}s`,
              batchNumber,
              preset.name,
              preset.applicantFields
            );
            // Update failed count for UI
            setFailedCount(getFailedApplicantsCount());
          }
        } else {
          throw error; // Re-throw non-timeout errors
        }
      }

      const allSettledTime = Date.now() - startAllSettled;
      Logger.debug(
        `✅ Promise.allSettled completed for batch ${batchNumber} in ${allSettledTime}ms. Got ${batchResults.length} results.`
      );
      Logger.debug(
        `📊 Batch ${batchNumber} results breakdown:`,
        batchResults.map((r) => ({
          status: r.status,
          success: r.status === 'fulfilled' ? r.value?.success : 'N/A',
          applicantNumber: r.status === 'fulfilled' ? r.value?.applicantNumber : 'N/A',
        }))
      );

      // Count results from this batch and calculate timing
      Logger.debug(`🔢 Counting results for batch ${batchNumber}...`);
      const batchSuccesses = batchResults.filter(
        (r) => r.status === 'fulfilled' && r.value?.success
      ).length;
      const batchFailures = batchResults.length - batchSuccesses;
      Logger.debug(
        `🔢 Batch ${batchNumber} counts: ${batchSuccesses} successes, ${batchFailures} failures out of ${batchResults.length} total`
      );

      // Calculate timing statistics for successful operations
      const successfulResults = batchResults
        .filter((r) => r.status === 'fulfilled' && r.value?.success)
        .map((r) => (r as any).value);

      const timingStats =
        successfulResults.length > 0
          ? {
              avgEvaluationTime: Math.round(
                successfulResults.reduce((sum, r) => sum + r.evaluationTime, 0) /
                  successfulResults.length
              ),
              avgAirtableTime: Math.round(
                successfulResults.reduce((sum, r) => sum + r.airtableTime, 0) /
                  successfulResults.length
              ),
              avgTotalTime: Math.round(
                successfulResults.reduce((sum, r) => sum + r.totalTime, 0) /
                  successfulResults.length
              ),
            }
          : null;

      totalSuccesses += batchSuccesses;
      totalFailures += batchFailures;
      processedCount += currentBatch.length;

      Logger.debug(
        `📈 Updated totals: ${totalSuccesses} total successes, ${totalFailures} total failures, ${processedCount} processed`
      );

      // Enhanced batch completion message with timing
      let batchMessage = `Batch ${batchNumber}/${totalBatches} complete: ${batchSuccesses} successes, ${batchFailures} failures.`;
      if (timedOut) {
        batchMessage += ' (TIMED OUT - some applicants saved for retry)';
      } else if (timingStats) {
        batchMessage += ` Avg times - Evaluation: ${timingStats.avgEvaluationTime}ms, Airtable: ${timingStats.avgAirtableTime}ms, Total: ${timingStats.avgTotalTime}ms`;
      }

      Logger.debug(`📊 ${batchMessage}`);

      // Update the user with progress after each batch
      Logger.debug('🖥️ Updating UI with batch completion message...');
      setResult(
        `Processed ${processedCount} of ${applicantsToProcess.length} applicants. ${totalSuccesses} successes, ${totalFailures} failures so far. ${batchMessage}${formatProcessingRate(processedCount, startTime)}`
      );
      Logger.debug('🖥️ UI updated. About to continue to next batch or finish.');

      // Check if we're at the end
      const nextBatchStart = batchStart + BATCH_SIZE;
      const hasMoreBatches = nextBatchStart < applicantsToProcess.length;
      Logger.debug(
        `🔄 Batch ${batchNumber} complete. Next start: ${nextBatchStart}, Has more batches: ${hasMoreBatches}`
      );

      if (!hasMoreBatches) {
        Logger.debug(
          `🏁 All batches completed! Final totals: ${totalSuccesses} successes, ${totalFailures} failures`
        );
      }
    }

    return { successes: totalSuccesses, failures: totalFailures };
  }

  // Validate prerequisites before running
  const validatePrerequisites = () => {
    // Check if user has permission to create records in evaluation table
    const createPermission = evaluationTable?.checkPermissionsForCreateRecord();
    if (!createPermission?.hasPermission) {
      const reason =
        'reasonDisplayString' in createPermission
          ? createPermission.reasonDisplayString
          : 'Permission denied';
      throw new Error(`Cannot create evaluation records: ${reason}`);
    }

    // Check if user has permission to update GlobalConfig (only editors and above)
    const configPermission = globalConfig.checkPermissionsForSet();
    if (!configPermission.hasPermission) {
      const reason =
        'reasonDisplayString' in configPermission
          ? configPermission.reasonDisplayString
          : 'Permission denied';
      throw new Error(`Cannot update settings: ${reason}`);
    }

    if (!applicantTable || !evaluationTable) {
      throw new Error('Please select both applicant and evaluation tables');
    }
    if (!preset.applicantViewId) {
      throw new Error('Please select an applicant view');
    }
    if (!preset.evaluationApplicantField) {
      throw new Error('Please select an applicant field in the evaluation table');
    }
    if (preset.applicantFields.length === 0) {
      throw new Error('Please select at least one applicant field');
    }
    if (preset.evaluationFields.length === 0) {
      throw new Error('Please select at least one evaluation field');
    }
  };

  // Handle the evaluation process
  const processEvaluation = async () => {
    // Get applicant records
    setResult('Getting applicant records...');
    const applicantView = applicantTable.getViewByIdIfExists(preset.applicantViewId);
    if (!applicantView) {
      throw new Error('Selected applicant view no longer exists');
    }

    // Only load the fields we actually need to reduce memory usage
    const fieldsToLoad = [
      ...preset.applicantFields.map((f) => f.fieldId),
      applicantTable.primaryField.id,
      // Add LinkedIn URL field if enrichment is enabled
      ...(preset.useLinkedinEnrichment && preset.linkedinUrlField ? [preset.linkedinUrlField] : []),
      // Add PDF resume field if enrichment is enabled
      ...(preset.usePdfResumeEnrichment && preset.pdfResumeField ? [preset.pdfResumeField] : []),
    ].filter(Boolean);
    
    Logger.debug(`🔍 Loading fields: ${fieldsToLoad.join(', ')}`);
    if (preset.useLinkedinEnrichment && preset.linkedinUrlField) {
      Logger.debug(`🔍 Including LinkedIn URL field: ${preset.linkedinUrlField}`);
    }
    if (preset.usePdfResumeEnrichment && preset.pdfResumeField) {
      Logger.debug(`📄 Including PDF resume field: ${preset.pdfResumeField}`);
    }

    const applicantRecords = await applicantView.selectRecordsAsync({
      fields: fieldsToLoad,
    });

    const previewText = renderPreviewText(
      applicantRecords.records.length,
      preset.evaluationFields.length,
      applicantRecords.records.map((record) => {
        const applicantData: Record<string, string> = {};
        // Convert applicant fields to string format for cost estimation
        for (const field of preset.applicantFields) {
          try {
            const key = field.questionName || field.fieldId;
            const value = record.getCellValueAsString(field.fieldId) || '';
            applicantData[key] = value;
          } catch (error) {
            // Skip fields that can't be read
          }
        }
        return applicantData;
      }),
      preset.evaluationFields.map((field) => ({ criteria: field.criteria }))
    );
    setResult(previewText);

    // Log detailed processing plan
    const planningConcurrency = (
      await import('../lib/concurrency/config')
    ).getCurrentConcurrency();
    const estimatedBatchSize = Math.max(
      1,
      Math.floor(planningConcurrency / preset.evaluationFields.length)
    );
    Logger.debug('📋 Processing Plan:');
    Logger.debug(`• Applicants to evaluate: ${applicantRecords.records.length}`);
    Logger.debug(`• Evaluation fields: ${preset.evaluationFields.length}`);
    Logger.debug(
      `• Total API calls needed: ${applicantRecords.records.length * preset.evaluationFields.length}`
    );
    Logger.debug(
      `• Configured concurrency: ${planningConcurrency} simultaneous API calls`
    );
    Logger.debug(`• Estimated batch size: ${estimatedBatchSize}`);
    Logger.debug(
      `• Expected batches: ${Math.ceil(applicantRecords.records.length / estimatedBatchSize)}`
    );
    Logger.debug(previewText);

    // Fast precheck to eliminate applicants that don't need processing
    setResult(
      `Starting pre-check for ${applicantRecords.records.length} applicants...`
    );
    const { applicantsToProcess, skippedApplicants } = await quickPrecheck(
      applicantRecords.records,
      preset,
      setProgress
    );

    setResult(
      `Pre-check complete: ${applicantsToProcess.length} applicants to process, ${skippedApplicants.length} skipped entirely because their dependency fields are empty.`
    );

    if (applicantsToProcess.length === 0) {
      return {
        message: `No applicants require processing. All ${skippedApplicants.length} applicants had empty dependency fields.`,
        skippedCount: skippedApplicants.length,
        successCount: 0,
        failureCount: 0,
      };
    }

    // Process applicants in batches to prevent browser overload
    const { successes, failures } = await processBatchedApplicants(
      applicantsToProcess,
      preset,
      evaluationTable,
      setProgress,
      setResult,
      processingStartTime
    );

    return {
      message: `Successfully created ${successes} evaluation(s) of ${
        applicantsToProcess.length
      } applicants. ${skippedApplicants.length} applicants were skipped entirely.${
        failures !== 0
          ? ` Failed ${failures} times. See console logs for failure details.`
          : ''
      }`,
      skippedCount: skippedApplicants.length,
      successCount: successes,
      failureCount: failures,
    };
  };

  const estimateCost = async () => {
    try {
      validatePrerequisites();

      // Get applicant records for cost estimation
      setResult('Calculating cost estimate...');
      const applicantView = applicantTable.getViewByIdIfExists(preset.applicantViewId);
      if (!applicantView) {
        throw new Error('Selected applicant view no longer exists');
      }

      // Only load the fields we actually need to reduce memory usage
      const fieldsToLoad = [
        ...preset.applicantFields.map((f) => f.fieldId),
        applicantTable.primaryField.id,
      ].filter(Boolean);

      const applicantRecords = await applicantView.selectRecordsAsync({
        fields: fieldsToLoad,
      });

      const previewText = renderPreviewText(
        applicantRecords.records.length,
        preset.evaluationFields.length,
        applicantRecords.records.map((record) => {
          const applicantData: Record<string, string> = {};
          // Convert applicant fields to string format for cost estimation
          for (const field of preset.applicantFields) {
            try {
              const key = field.questionName || field.fieldId;
              const value = record.getCellValueAsString(field.fieldId) || '';
              applicantData[key] = value;
            } catch (error) {
              // Skip fields that can't be read
            }
          }
          return applicantData;
        }),
        preset.evaluationFields.map((field) => ({ criteria: field.criteria }))
      );

      setResult(previewText);
    } catch (error) {
      const errorMessage = `Cost estimation error: ${error instanceof Error ? error.message : String(error)}`;
      setResult(errorMessage);
    }
  };

  const run = async () => {
    setRunning(true);
    setProgress(0);
    setResult(null);
    setProcessingStartTime(Date.now());
    Logger.debug('Running preset', preset);
    
    // Log enrichment configuration details
    Logger.debug("🧩 Current preset enrichment configuration:", {
      useLinkedinEnrichment: preset.useLinkedinEnrichment,
      linkedinUrlField: preset.linkedinUrlField,
      linkedinDataField: preset.linkedinDataField,
      usePdfResumeEnrichment: preset.usePdfResumeEnrichment,
      pdfResumeField: preset.pdfResumeField, 
      pdfResumeDataField: preset.pdfResumeDataField
    });

    try {
      validatePrerequisites();
      const result = await processEvaluation();
      setResult(result.message);

      // Show failed applicants modal if there are any failures after processing
      const currentFailedCount = getFailedApplicantsCount();
      if (currentFailedCount > 0) {
        setFailedCount(currentFailedCount);
        setShowFailedModal(true);
      }
    } catch (error) {
      const errorMessage = `Error: ${error instanceof Error ? error.message : String(error)}`;
      setResult(errorMessage);
    } finally {
      setRunning(false);
      setProcessingStartTime(null);
    }
  };

  const handleRetryFailed = async () => {
    if (!applicantTable || !evaluationTable) return;

    setIsRetrying(true);
    setProgress(0);
    setResult(null);
    const retryStartTime = Date.now();

    try {
      const failedApplicants = getFailedApplicants();
      const retryResult = await retryFailedApplicants(
        failedApplicants,
        preset,
        applicantTable,
        evaluationTable,
        setProgress,
        setResult,
        retryStartTime
      );

      setResult(
        `Retry complete: ${retryResult.successes} successes, ${retryResult.failures} failures${formatProcessingRate(retryResult.successes + retryResult.failures, retryStartTime)}`
      );

      // Update failed count
      const newFailedCount = getFailedApplicantsCount();
      setFailedCount(newFailedCount);

      // Close modal if no failures remain
      if (newFailedCount === 0) {
        setShowFailedModal(false);
      }
    } catch (error) {
      const errorMessage = `Retry error: ${error instanceof Error ? error.message : String(error)}`;
      setResult(errorMessage);
    } finally {
      setIsRetrying(false);
    }
  };

  const handleClearFailed = async () => {
    await clearFailedApplicants();
    setFailedCount(0);
    setShowFailedModal(false);
  };

  /**
   * Handle debug API info button click - displays current API keys and model status
   */
  const handleDebugApiInfo = () => {
    import('../lib/getChatCompletion/apiKeyManager').then((module) => {
      const openAiKey = module.getOpenAiApiKey();
      const anthropicKey = module.getAnthropicApiKey();
      const selectedProvider = module.getSelectedModelProvider();
      const openAiModel = module.getOpenAiModelName();
      const anthropicModel = module.getAnthropicModelName();
      const activeModelName =
        selectedProvider === 'openai' ? openAiModel : anthropicModel;

      // Create debug info element
      const debugInfo = document.createElement('div');
      debugInfo.className = 'mt-2 p-1 bg-blue-100 rounded';
      debugInfo.innerHTML = `
        <p>${PROVIDER_ICONS[selectedProvider] || '🔧'} <strong>Provider:</strong> ${selectedProvider === 'openai' ? 'OpenAI' : 'Anthropic Claude'}</p>
        <p>📋 <strong>Model:</strong> ${formatModelName(activeModelName)}</p>
        <p>🔑 <strong>API Keys:</strong> OpenAI: ${openAiKey ? '✅' : '❌'}, Anthropic: ${anthropicKey ? '✅' : '❌'}</p>
      `;

      // Find debug container and update it
      const debugDiv = document.querySelector('.mb-4.p-2.bg-gray-100.rounded.text-xs');
      if (debugDiv) {
        const existingInfo = debugDiv.querySelector('.mt-2.p-1.bg-blue-100.rounded');
        if (existingInfo) {
          existingInfo.remove();
        }
        debugDiv.appendChild(debugInfo);
      }
    });
  };

  return (
    <div className="space-y-4">
      {/* API Keys Debug block */}
      <div className="mb-4 p-2 bg-gray-100 rounded text-xs">
        <p>
          API Key config:{' '}
          <button
            type="button"
            onClick={handleDebugApiInfo}
            className="underline text-blue-500"
          >
            Check API Keys and Model
          </button>
        </p>
      </div>
      {/* End API Keys Debug Block */}

      <FormFieldWithTooltip
        label="Applicant table"
        helpKey="applicantTable"
        showGuidedHelp={showGuidedHelp}
      >
        <TablePickerSynced
          globalConfigKey={['presets', preset.name, 'applicantTableId']}
          onChange={() => {
            globalConfig.setAsync(['presets', preset.name, 'applicantViewId'], '');
            globalConfig.setAsync(['presets', preset.name, 'applicantFields'], []);
          }}
        />
      </FormFieldWithTooltip>
      {applicantTable && (
        <>
          <FormFieldWithTooltip
            label="Applicant view"
            helpKey="applicantView"
            showGuidedHelp={showGuidedHelp}
          >
            <ViewPickerSynced
              globalConfigKey={['presets', preset.name, 'applicantViewId']}
              table={applicantTable}
            />
          </FormFieldWithTooltip>
          <FormField label="Answer (input) fields">
            <div className="flex flex-col gap-3">
              {preset.applicantFields.map((field, index) => (
                <ApplicantFieldEditor
                  key={`applicant-field-${field.fieldId || ''}-${index}`}
                  preset={preset}
                  index={index}
                />
              ))}
              <ApplicantFieldEditor
                key={`applicant-new-field-${preset.applicantFields.length}`}
                preset={preset}
                index={preset.applicantFields.length}
              />
            </div>
          </FormField>
        </>
      )}

      <FormFieldWithTooltip
        label="Evaluation table"
        helpKey="evaluationTable"
        showGuidedHelp={showGuidedHelp}
      >
        <TablePickerSynced
          globalConfigKey={['presets', preset.name, 'evaluationTableId']}
          onChange={() => {
            globalConfig.setAsync(['presets', preset.name, 'evaluationFields'], []);
            globalConfig.setAsync(
              ['presets', preset.name, 'evaluationLogsField'],
              undefined
            );
          }}
        />
      </FormFieldWithTooltip>
      {evaluationTable && (
        <>
          <FormField label="Score (output) fields">
            <div className="flex flex-col gap-3">
              {preset.evaluationFields.map((field, index) => (
                <EvaluationFieldEditor
                  key={`eval-field-${field.fieldId || ''}-${index}`}
                  preset={preset}
                  index={index}
                />
              ))}
              <EvaluationFieldEditor
                key={`eval-new-field-${preset.evaluationFields.length}`}
                preset={preset}
                index={preset.evaluationFields.length}
              />
            </div>
          </FormField>
          <FormFieldWithTooltip
            label="Applicant field"
            helpKey="applicantField"
            showGuidedHelp={showGuidedHelp}
          >
            <FieldPickerSynced
              allowedTypes={[FieldType.MULTIPLE_RECORD_LINKS]}
              globalConfigKey={['presets', preset.name, 'evaluationApplicantField']}
              table={evaluationTable}
            />
          </FormFieldWithTooltip>
          <FormFieldWithTooltip
            label="(optional) Logs field"
            helpKey="logsField"
            showGuidedHelp={showGuidedHelp}
          >
            <FieldPickerSynced
              allowedTypes={[
                FieldType.SINGLE_LINE_TEXT,
                FieldType.MULTILINE_TEXT,
                FieldType.RICH_TEXT,
              ]}
              globalConfigKey={['presets', preset.name, 'evaluationLogsField']}
              table={evaluationTable}
              shouldAllowPickingNone={true}
            />
          </FormFieldWithTooltip>
          
          {/* Server-specific features section */}
          {isServerModeEnabled() && (
            <>
              <div className="mt-4 mb-2 p-2 bg-blue-50 rounded">
                <div className="font-bold mb-2">Server Features</div>
                <p className="text-sm text-gray-600 mb-3">
                  The following features require server mode to be enabled.
                </p>
                
                {/* LinkedIn Enrichment Options */}
                <FormFieldWithTooltip
                  label="LinkedIn Enrichment"
                  helpKey="linkedinEnrichment"
                  showGuidedHelp={showGuidedHelp}
                >
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="useLinkedinEnrichment"
                      className="mr-2"
                      checked={preset.useLinkedinEnrichment || false}
                      onChange={(e) => {
                        upsertPreset({
                          ...preset,
                          useLinkedinEnrichment: e.target.checked,
                        });
                      }}
                    />
                    <label htmlFor="useLinkedinEnrichment">
                      Enhance evaluations with LinkedIn profile data
                    </label>
                  </div>
                </FormFieldWithTooltip>
                
                {preset.useLinkedinEnrichment && (
                  <FormFieldWithTooltip
                    label="LinkedIn URL Field"
                    helpKey="linkedinUrlField"
                    showGuidedHelp={showGuidedHelp}
                  >
                    <FieldPickerSynced
                      table={applicantTable}
                      allowedTypes={[
                        FieldType.SINGLE_LINE_TEXT,
                        FieldType.URL,
                      ]}
                      globalConfigKey={['presets', preset.name, 'linkedinUrlField']}
                      shouldAllowPickingNone={true}
                    />
                  </FormFieldWithTooltip>
                )}
                
                {preset.useLinkedinEnrichment && (
                  <FormFieldWithTooltip
                    label="(optional) LinkedIn Data Field"
                    helpKey="linkedinDataField"
                    showGuidedHelp={showGuidedHelp}
                  >
                    <FieldPickerSynced
                      table={evaluationTable}
                      allowedTypes={[
                        FieldType.SINGLE_LINE_TEXT,
                        FieldType.MULTILINE_TEXT,
                        FieldType.RICH_TEXT,
                      ]}
                      globalConfigKey={['presets', preset.name, 'linkedinDataField']}
                      shouldAllowPickingNone={true}
                    />
                  </FormFieldWithTooltip>
                )}
                
                {/* Multi-Axis Evaluation Options */}
                <FormFieldWithTooltip
                  label="Multi-Axis Evaluation"
                  helpKey="multiAxisEvaluation"
                  showGuidedHelp={showGuidedHelp}
                >
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="useMultiAxisEvaluation"
                      className="mr-2"
                      checked={preset.useMultiAxisEvaluation || false}
                      onChange={(e) => {
                        upsertPreset({
                          ...preset,
                          useMultiAxisEvaluation: e.target.checked,
                        });
                      }}
                    />
                    <label htmlFor="useMultiAxisEvaluation">
                      Use multi-dimensional evaluation (assesses candidates across multiple axes)
                    </label>
                  </div>
                </FormFieldWithTooltip>
              </div>
            </>
          )}
          
          {/* Show a warning if server mode is not enabled but these features are */}
          {!isServerModeEnabled() && (preset.useLinkedinEnrichment || preset.useMultiAxisEvaluation) && (
            <div className="mt-2 mb-4 p-2 bg-yellow-100 rounded text-yellow-800">
              <strong>Warning:</strong> You have LinkedIn enrichment or multi-axis evaluation enabled, but server mode is disabled. 
              These features require server mode to work properly. Please enable server mode in the settings.
            </div>
          )}
          
          {preset.useMultiAxisEvaluation && (
            <>
              <div className="mt-4 mb-2 p-2 bg-gray-100 rounded">
                <div className="font-bold mb-2">Multi-Axis Output Fields</div>
                <p className="text-sm text-gray-600 mb-3">
                  Select output fields for each evaluation axis. These should be numeric fields (Number, Rating, etc.) that will store the 1-5 rating for each dimension.
                </p>

                {/* General Promise Field */}
                <FormFieldWithTooltip
                  label="General Promise Score Field"
                  helpKey="outputField"
                  showGuidedHelp={showGuidedHelp}
                >
                  <FieldPickerSynced
                    table={evaluationTable}
                    allowedTypes={[
                      FieldType.NUMBER,
                      FieldType.PERCENT,
                      FieldType.RATING,
                    ]}
                    globalConfigKey={['presets', preset.name, 'generalPromiseField']}
                    shouldAllowPickingNone={true}
                  />
                </FormFieldWithTooltip>

                {/* ML Skills Field */}
                <FormFieldWithTooltip
                  label="ML Skills Score Field"
                  helpKey="outputField"
                  showGuidedHelp={showGuidedHelp}
                >
                  <FieldPickerSynced
                    table={evaluationTable}
                    allowedTypes={[
                      FieldType.NUMBER,
                      FieldType.PERCENT,
                      FieldType.RATING,
                    ]}
                    globalConfigKey={['presets', preset.name, 'mlSkillsField']}
                    shouldAllowPickingNone={true}
                  />
                </FormFieldWithTooltip>

                {/* Software Engineering Field */}
                <FormFieldWithTooltip
                  label="Software Engineering Score Field"
                  helpKey="outputField"
                  showGuidedHelp={showGuidedHelp}
                >
                  <FieldPickerSynced
                    table={evaluationTable}
                    allowedTypes={[
                      FieldType.NUMBER,
                      FieldType.PERCENT,
                      FieldType.RATING,
                    ]}
                    globalConfigKey={['presets', preset.name, 'softwareEngineeringField']}
                    shouldAllowPickingNone={true}
                  />
                </FormFieldWithTooltip>

                {/* Policy Experience Field */}
                <FormFieldWithTooltip
                  label="Policy Experience Score Field"
                  helpKey="outputField"
                  showGuidedHelp={showGuidedHelp}
                >
                  <FieldPickerSynced
                    table={evaluationTable}
                    allowedTypes={[
                      FieldType.NUMBER,
                      FieldType.PERCENT,
                      FieldType.RATING,
                    ]}
                    globalConfigKey={['presets', preset.name, 'policyExperienceField']}
                    shouldAllowPickingNone={true}
                  />
                </FormFieldWithTooltip>

                {/* AI Safety Understanding Field */}
                <FormFieldWithTooltip
                  label="AI Safety Understanding Score Field"
                  helpKey="outputField"
                  showGuidedHelp={showGuidedHelp}
                >
                  <FieldPickerSynced
                    table={evaluationTable}
                    allowedTypes={[
                      FieldType.NUMBER,
                      FieldType.PERCENT,
                      FieldType.RATING,
                    ]}
                    globalConfigKey={['presets', preset.name, 'aiSafetyUnderstandingField']}
                    shouldAllowPickingNone={true}
                  />
                </FormFieldWithTooltip>

                {/* Path to Impact Field */}
                <FormFieldWithTooltip
                  label="Path to Impact Score Field"
                  helpKey="outputField"
                  showGuidedHelp={showGuidedHelp}
                >
                  <FieldPickerSynced
                    table={evaluationTable}
                    allowedTypes={[
                      FieldType.NUMBER,
                      FieldType.PERCENT,
                      FieldType.RATING,
                    ]}
                    globalConfigKey={['presets', preset.name, 'pathToImpactField']}
                    shouldAllowPickingNone={true}
                  />
                </FormFieldWithTooltip>

                {/* Research Experience Field */}
                <FormFieldWithTooltip
                  label="Research Experience Score Field"
                  helpKey="outputField"
                  showGuidedHelp={showGuidedHelp}
                >
                  <FieldPickerSynced
                    table={evaluationTable}
                    allowedTypes={[
                      FieldType.NUMBER,
                      FieldType.PERCENT,
                      FieldType.RATING,
                    ]}
                    globalConfigKey={['presets', preset.name, 'researchExperienceField']}
                    shouldAllowPickingNone={true}
                  />
                </FormFieldWithTooltip>
              </div>

              <FormFieldWithTooltip
                label="(optional) Multi-Axis Data Field"
                helpKey="multiAxisDataField"
                showGuidedHelp={showGuidedHelp}
              >
                <FieldPickerSynced
                  table={evaluationTable}
                  allowedTypes={[
                    FieldType.SINGLE_LINE_TEXT,
                    FieldType.MULTILINE_TEXT,
                    FieldType.RICH_TEXT,
                  ]}
                  globalConfigKey={['presets', preset.name, 'multiAxisDataField']}
                  shouldAllowPickingNone={true}
                />
              </FormFieldWithTooltip>
            </>
          )}
          
          {/* PDF Resume Enrichment Options */}
          <FormFieldWithTooltip
            label="PDF Resume Enrichment"
            helpKey="pdfResumeEnrichment"
            showGuidedHelp={showGuidedHelp}
          >
            <div className="flex items-center">
              <input
                type="checkbox"
                id="usePdfResumeEnrichment"
                className="mr-2"
                checked={preset.usePdfResumeEnrichment || false}
                onChange={(e) => {
                  upsertPreset({
                    ...preset,
                    usePdfResumeEnrichment: e.target.checked,
                  });
                }}
              />
              <label htmlFor="usePdfResumeEnrichment">
                Enhance evaluations with PDF resume data
              </label>
            </div>
          </FormFieldWithTooltip>
          
          {preset.usePdfResumeEnrichment && (
            <FormFieldWithTooltip
              label="PDF Resume Field"
              helpKey="pdfResumeField"
              showGuidedHelp={showGuidedHelp}
            >
              <FieldPickerSynced
                table={applicantTable}
                globalConfigKey={['presets', preset.name, 'pdfResumeField']}
                shouldAllowPickingNone={true}
              />
            </FormFieldWithTooltip>
          )}
          
          {preset.usePdfResumeEnrichment && (
            <FormFieldWithTooltip
              label="(optional) PDF Resume Data Field"
              helpKey="pdfResumeDataField"
              showGuidedHelp={showGuidedHelp}
            >
              <FieldPickerSynced
                table={evaluationTable}
                allowedTypes={[
                  FieldType.SINGLE_LINE_TEXT,
                  FieldType.MULTILINE_TEXT,
                  FieldType.RICH_TEXT,
                ]}
                globalConfigKey={['presets', preset.name, 'pdfResumeDataField']}
                shouldAllowPickingNone={true}
              />
            </FormFieldWithTooltip>
          )}
        </>
      )}

      <div className="flex gap-2">
        <Button
          type="button"
          variant="default"
          icon="formula"
          onClick={estimateCost}
          disabled={running}
        >
          Estimate Cost
        </Button>
        <Button
          type="button"
          variant="primary"
          icon="play"
          onClick={run}
          disabled={running}
        >
          Run
        </Button>
        {failedCount > 0 && (
          <Button
            type="button"
            variant="secondary"
            icon="trash"
            onClick={async () => {
              await clearFailedApplicants();
              setFailedCount(0);
            }}
            disabled={running}
            aria-label={`Clear ${failedCount} failed applicants`}
          >
            Clear Failed ({failedCount})
          </Button>
        )}
      </div>
      {running && <ProgressBar className="my-2" progress={progress} />}
      {result && <Text className="my-2">{result}</Text>}

      <FailedApplicantsModal
        failedApplicants={getFailedApplicants()}
        isOpen={showFailedModal}
        onClose={() => setShowFailedModal(false)}
        onRetryFailed={handleRetryFailed}
        onClearFailed={handleClearFailed}
        isRetrying={isRetrying}
      />
    </div>
  );
};

interface FieldEditorProps {
  preset: Preset;
  index: number;
}

const ApplicantFieldEditor: React.FC<FieldEditorProps> = ({ preset, index }) => {
  const applicantField = preset.applicantFields[index] ?? { fieldId: '' };
  const isExistingField = index < preset.applicantFields.length;
  const showGuidedHelp = useGuidedMode();

  const base = useBase();
  const applicantTable = base.getTableByIdIfExists(preset.applicantTableId);

  const [field, setField] = useState<Field>(
    applicantTable.getFieldByIdIfExists(applicantField.fieldId)
  );
  const [questionName, setQuestionName] = useState<string>(
    applicantField.questionName ?? ''
  );

  const saveField = (applicantField: Preset['applicantFields'][number]) => {
    // delete
    if (!applicantField.fieldId) {
      upsertPreset({
        ...preset,
        applicantFields: preset.applicantFields.filter((_, i) => i !== index),
      });
      // create
    } else if (index >= preset.applicantFields.length) {
      upsertPreset({
        ...preset,
        applicantFields: [...preset.applicantFields, applicantField],
      });
    } else {
      upsertPreset({
        ...preset,
        applicantFields: preset.applicantFields.map((original, i) =>
          i === index ? applicantField : original
        ),
      });
    }
  };

  const handleDelete = () => {
    upsertPreset({
      ...preset,
      applicantFields: preset.applicantFields.filter((_, i) => i !== index),
    });
  };

  return (
    <div className="p-3 border bg-white rounded shadow">
      <div className="grid grid-cols-2 gap-3">
        <FormFieldWithTooltip
          label="Source field"
          helpKey="sourceField"
          showGuidedHelp={showGuidedHelp}
          className="mb-0"
        >
          <FieldPicker
            table={applicantTable}
            shouldAllowPickingNone={true}
            onChange={(field) => {
              setField(field);
              saveField({ ...applicantField, fieldId: field?.id });
            }}
            field={field}
          />
        </FormFieldWithTooltip>
        <FormFieldWithTooltip
          label="(optional) Question name"
          helpKey="questionName"
          showGuidedHelp={showGuidedHelp}
          className="mb-0"
        >
          <Input
            value={questionName}
            onChange={(event) => {
              setQuestionName(event.target.value);
              saveField({
                ...applicantField,
                questionName: event.target.value || undefined,
              });
            }}
          />
        </FormFieldWithTooltip>
      </div>
      {isExistingField && (
        <div className="mt-3 flex justify-end">
          <Button
            variant="danger"
            size="small"
            icon="trash"
            onClick={handleDelete}
            aria-label="Delete input field"
          >
            Delete
          </Button>
        </div>
      )}
    </div>
  );
};

const EvaluationFieldEditor: React.FC<FieldEditorProps> = ({ preset, index }) => {
  const evaluationField = preset.evaluationFields[index] ?? {
    fieldId: '',
    criteria: '',
    dependsOnInputField: undefined,
  };
  const isExistingField = index < preset.evaluationFields.length;
  const showGuidedHelp = useGuidedMode();

  const base = useBase();
  const evaluationTable = base.getTableByIdIfExists(preset.evaluationTableId);
  const applicantTable = base.getTableByIdIfExists(preset.applicantTableId);

  const [field, setField] = useState<Field>(
    evaluationTable.getFieldByIdIfExists(evaluationField.fieldId)
  );
  const [criteria, setCriteria] = useState<string>(evaluationField.criteria ?? '');
  // We don't use the dependsOnField value directly, but we need the setter
  const [, setDependsOnField] = useState<Field | null>(
    evaluationField.dependsOnInputField
      ? applicantTable?.getFieldByIdIfExists(evaluationField.dependsOnInputField)
      : null
  );

  // Create options for the dependency dropdown from the applicant fields
  const inputFieldOptions = useMemo(() => {
    if (!applicantTable) return [{ value: '', label: 'None' }];

    const options = [{ value: '', label: 'None (always evaluate)' }];

    for (const { fieldId } of preset.applicantFields) {
      const field = applicantTable.getFieldByIdIfExists(fieldId);
      if (field) {
        options.push({
          value: fieldId,
          label: field.name,
        });
      }
    }

    return options;
  }, [applicantTable, preset.applicantFields]);

  const saveField = (evaluationField: Preset['evaluationFields'][number]) => {
    // delete
    if (!evaluationField.fieldId) {
      upsertPreset({
        ...preset,
        evaluationFields: preset.evaluationFields.filter((_, i) => i !== index),
      });
      // create
    } else if (index >= preset.evaluationFields.length) {
      upsertPreset({
        ...preset,
        evaluationFields: [...preset.evaluationFields, evaluationField],
      });
    } else {
      upsertPreset({
        ...preset,
        evaluationFields: preset.evaluationFields.map((original, i) =>
          i === index ? evaluationField : original
        ),
      });
    }
  };

  const handleDelete = () => {
    upsertPreset({
      ...preset,
      evaluationFields: preset.evaluationFields.filter((_, i) => i !== index),
    });
  };

  return (
    <div className="p-3 border bg-white rounded shadow">
      <div className="grid grid-cols-2 gap-3">
        <FormFieldWithTooltip
          label="Output field"
          helpKey="outputField"
          showGuidedHelp={showGuidedHelp}
          className="mb-0"
        >
          <FieldPicker
            allowedTypes={[FieldType.NUMBER, FieldType.PERCENT, FieldType.RATING]}
            table={evaluationTable}
            shouldAllowPickingNone={true}
            onChange={(field) => {
              setField(field);
              saveField({ ...evaluationField, fieldId: field?.id });
            }}
            field={field}
          />
        </FormFieldWithTooltip>
        <FormFieldWithTooltip
          label="Evaluation criteria"
          helpKey="evaluationCriteria"
          showGuidedHelp={showGuidedHelp}
          className="mb-0"
        >
          <Input
            value={criteria}
            onChange={(event) => {
              setCriteria(event.target.value);
              saveField({
                ...evaluationField,
                criteria: event.target.value || undefined,
              });
            }}
          />
        </FormFieldWithTooltip>
      </div>
      <FormFieldWithTooltip
        label="Only evaluate if this input field is not empty:"
        helpKey="dependencyField"
        showGuidedHelp={showGuidedHelp}
        className="mb-0 mt-3"
      >
        <Select
          options={inputFieldOptions}
          value={evaluationField.dependsOnInputField || ''}
          onChange={(value) => {
            const dependsOnInputField = value === '' ? undefined : value;
            setDependsOnField(
              dependsOnInputField
                ? applicantTable?.getFieldByIdIfExists(dependsOnInputField as string)
                : null
            );
            saveField({
              ...evaluationField,
              dependsOnInputField: dependsOnInputField as string | undefined,
            });
          }}
        />
      </FormFieldWithTooltip>
      {isExistingField && (
        <div className="mt-3 flex justify-end">
          <Button
            variant="danger"
            size="small"
            icon="trash"
            onClick={handleDelete}
            aria-label="Delete output field"
          >
            Delete
          </Button>
        </div>
      )}
    </div>
  );
};
