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
  useBase,
  ViewPickerSynced,
} from '@airtable/blocks/ui';
import React from 'react';
import { useState, useMemo } from 'react';

import { type Preset, upsertPreset, useSelectedPreset } from '../lib/preset';
import { globalConfig } from '@airtable/blocks';
import {
  type Field,
  FieldType,
  type Record as AirtableRecord,
  type Table,
} from '@airtable/blocks/models';
import { evaluateApplicants, type SetProgress } from '../lib/evaluateApplicants';
import pRetry from 'p-retry';

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
const shouldProcessApplicant = (applicant: AirtableRecord, dependencyFields: string[]): boolean => {
  // Check each dependency field
  for (const inputFieldId of dependencyFields) {
    // If any required field has a value, we need to process this applicant
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
const renderPreviewText = (
  numberOfApplicants: number,
  numberOfEvaluationCriteria: number
) => {
  const numberOfItems = numberOfApplicants * numberOfEvaluationCriteria;
  const timeEstimateMins = ((numberOfItems * 0.9) / 60).toFixed(1); // speed roughly for gpt-4-1106-preview, at 30 request concurrency
  const costEstimateGbp = (numberOfItems * 0.011).toFixed(2); // pricing roughly for gpt-4-1106-preview
  return `Found ${numberOfApplicants} records, and ${numberOfEvaluationCriteria} evaluation criteria for a total of ${numberOfItems} items to process. Estimated time: ${timeEstimateMins} min. Estimated cost: £${costEstimateGbp}. To cancel, please close the entire browser tab.`;
};

export const MainPage = () => {
  const preset = useSelectedPreset();

  const base = useBase();
  const applicantTable = base.getTableByIdIfExists(preset.applicantTableId);
  const evaluationTable = base.getTableByIdIfExists(preset.evaluationTableId);

  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0); // between 0.0 and 1.0
  const [result, setResult] = useState<string>(null);
  /**
   * Process applicants in batches to prevent browser overload
   * Works with the existing LLM API concurrency limits
   */
  async function processBatchedApplicants(
    applicantsToProcess: AirtableRecord[],
    preset: Preset,
    evaluationTable: Table,
    setProgress: (updater: (prev: number) => number) => void,
    setResult: (result: string) => void
  ): Promise<{ successes: number; failures: number }> {
    // Dynamic batch sizing based on field count to optimize concurrency
    const fieldCount = preset.evaluationFields.length;
    const BATCH_SIZE = Math.max(1, Math.floor(30 / fieldCount));

    console.log(
      `Processing with batch size of ${BATCH_SIZE} applicants per batch ` +
        `(${fieldCount} fields each, optimized for 30 concurrent API calls)`
    );

    let totalSuccesses = 0;
    let totalFailures = 0;
    let processedCount = 0;

    // Process in batches to manage memory
    for (
      let batchStart = 0;
      batchStart < applicantsToProcess.length;
      batchStart += BATCH_SIZE
    ) {
      // Extract the current batch
      const currentBatch = applicantsToProcess.slice(
        batchStart,
        Math.min(batchStart + BATCH_SIZE, applicantsToProcess.length)
      );

      const batchNumber = Math.floor(batchStart / BATCH_SIZE) + 1;
      const totalBatches = Math.ceil(applicantsToProcess.length / BATCH_SIZE);

      setResult(
        `Processing batch ${batchNumber} of ${totalBatches} ` +
          `(applicants ${batchStart + 1}-${Math.min(
            batchStart + BATCH_SIZE,
            applicantsToProcess.length
          )} ` +
          `of ${applicantsToProcess.length})`
      );

      // Get evaluation promises for this batch only
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
        }
      );

      // Process each evaluation and write to Airtable
      const batchResults = await Promise.allSettled(
        batchEvaluationPromises.map(async (evaluationPromise) => {
          try {
            const evaluation = await evaluationPromise;

            // Check if evaluation contains applicant ID before logging
            const applicantId = evaluation[preset.evaluationApplicantField]?.[0]?.id;
            console.log(
              `Evaluated applicant ${
                applicantId || 'unknown'
              }, uploading to Airtable...`
            );

            // Write to Airtable with retry
            await pRetry(() => evaluationTable.createRecordAsync(evaluation));
            return { success: true };
          } catch (error) {
            console.error('Failed to evaluate applicant', error);
            return { success: false, error };
          }
        })
      );

      // Count results from this batch
      const batchSuccesses = batchResults.filter(
        (r) => r.status === 'fulfilled' && r.value?.success
      ).length;
      const batchFailures = batchResults.length - batchSuccesses;

      totalSuccesses += batchSuccesses;
      totalFailures += batchFailures;
      processedCount += currentBatch.length;

      // Update the user with progress after each batch
      setResult(
        `Processed ${processedCount} of ${applicantsToProcess.length} applicants. ` +
          `${totalSuccesses} successes, ${totalFailures} failures so far. ` +
          `Batch ${batchNumber}/${totalBatches} complete.`
      );
    }

    return { successes: totalSuccesses, failures: totalFailures };
  }

  // Validate prerequisites before running
  const validatePrerequisites = () => {
    if (!applicantTable) throw new Error('Could not access applicant table');
    if (!evaluationTable) throw new Error('Could not access evaluation table');
    if (!preset.applicantFields.length) throw new Error('No input fields selected');
    if (!preset.evaluationFields.length) throw new Error('No output fields selected');
  };

  // Handle the evaluation process
  const processEvaluation = async () => {
    // Get applicant records
    setResult('Getting applicant records...');
    const applicantView = applicantTable.getViewById(preset.applicantViewId);
    const applicantRecords = await applicantView.selectRecordsAsync();
    
    setResult(
      renderPreviewText(
        applicantRecords.records.length,
        preset.evaluationFields.length
      )
    );

    // Fast precheck to eliminate applicants that don't need processing
    setResult(`Starting pre-check for ${applicantRecords.records.length} applicants...`);
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
        failureCount: 0
      };
    }

    // Process applicants in batches to prevent browser overload
    const { successes, failures } = await processBatchedApplicants(
      applicantsToProcess,
      preset,
      evaluationTable,
      setProgress,
      setResult
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
      failureCount: failures
    };
  };

  const run = async () => {
    setRunning(true);
    setProgress(0);
    setResult(null);
    console.log('Running preset', preset);
    
    try {
      validatePrerequisites();
      const result = await processEvaluation();
      setResult(result.message);
    } catch (error) {
      const errorMessage =
        `Error: ${error instanceof Error ? error.message : String(error)}`;
      setResult(errorMessage);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mb-24">
      <FormField label="Applicant table">
        <TablePickerSynced
          globalConfigKey={['presets', preset.name, 'applicantTableId']}
          onChange={() => {
            globalConfig.setAsync(['presets', preset.name, 'applicantViewId'], '');
            globalConfig.setAsync(['presets', preset.name, 'applicantFields'], []);
          }}
        />
      </FormField>
      {applicantTable && (
        <>
          <FormField label="Applicant view">
            <ViewPickerSynced
              globalConfigKey={['presets', preset.name, 'applicantViewId']}
              table={applicantTable}
            />
          </FormField>
          <FormField label="Answer (input) fields">
            <div className="flex flex-col gap-2">
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

      <FormField label="Evaluation table">
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
      </FormField>
      {evaluationTable && (
        <>
          <FormField label="Score (output) fields">
            <div className="flex flex-col gap-2">
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
          <FormField label="Applicant field">
            <FieldPickerSynced
              allowedTypes={[FieldType.MULTIPLE_RECORD_LINKS]}
              globalConfigKey={['presets', preset.name, 'evaluationApplicantField']}
              table={evaluationTable}
            />
          </FormField>
          <FormField label="(optional) Logs field">
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
          </FormField>
        </>
      )}

      <Button
        type="button"
        variant="primary"
        icon="play"
        onClick={run}
        disabled={running}
      >
        Run
      </Button>
      {running && <ProgressBar className="my-2" progress={progress} />}
      {result && <Text className="my-2">{result}</Text>}
    </div>
  );
};

interface FieldEditorProps {
  preset: Preset;
  index: number;
}

const ApplicantFieldEditor: React.FC<FieldEditorProps> = ({ preset, index }) => {
  const applicantField = preset.applicantFields[index] ?? { fieldId: '' };

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

  return (
    <div className="p-2 border bg-white rounded shadow grid grid-cols-2 gap-2">
      <FormField label="Source field" className="mb-0">
        <FieldPicker
          table={applicantTable}
          shouldAllowPickingNone={true}
          onChange={(field) => {
            setField(field);
            saveField({ ...applicantField, fieldId: field?.id });
          }}
          field={field}
        />
      </FormField>
      <FormField label="(optional) Question name" className="mb-0">
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
      </FormField>
    </div>
  );
};

const EvaluationFieldEditor: React.FC<FieldEditorProps> = ({ preset, index }) => {
  const evaluationField = preset.evaluationFields[index] ?? {
    fieldId: '',
    criteria: '',
    dependsOnInputField: undefined,
  };

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

  return (
    <div className="p-2 border bg-white rounded shadow grid grid-cols-2 gap-2">
      <FormField label="Output field" className="mb-0">
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
      </FormField>
      <FormField label="Evaluation criteria" className="mb-0">
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
      </FormField>
      <FormField
        label="Only evaluate if this input field is not empty:"
        className="mb-0 col-span-2"
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
      </FormField>
    </div>
  );
};
