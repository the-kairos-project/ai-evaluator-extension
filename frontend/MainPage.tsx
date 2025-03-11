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
} from "@airtable/blocks/ui";
import React, { useState, useMemo } from "react";
import { Preset, upsertPreset, useSelectedPreset } from "../lib/preset";
import { globalConfig } from "@airtable/blocks";
import { Field, FieldType, Record as AirtableRecord } from "@airtable/blocks/models";
import { evaluateApplicants, SetProgress } from "../lib/evaluateApplicants";
import pRetry from "p-retry";

// Fast precheck function to filter out applicants that don't need processing
const quickPrecheck = async (
  applicants: AirtableRecord[],
  preset: Preset,
  setProgress: SetProgress,
) => {
  // Create a dependency map for quick lookups
  const dependencyMap = new Map<string, string[]>();
  
  // For each evaluation field that has a dependency, record that information
  preset.evaluationFields.forEach(({ fieldId, dependsOnInputField }) => {
    if (dependsOnInputField) {
      if (!dependencyMap.has(dependsOnInputField)) {
        dependencyMap.set(dependsOnInputField, []);
      }
      dependencyMap.get(dependsOnInputField).push(fieldId);
    }
  });
  
  // If no dependencies, process all applicants
  if (dependencyMap.size === 0) {
    return { 
      applicantsToProcess: applicants,
      skippedApplicants: []
    };
  }
  
  // Fast check on each applicant
  const applicantsToProcess = [];
  const skippedApplicants = [];
  
  // Process in small batches to show progress
  const batchSize = 100;
  for (let i = 0; i < applicants.length; i += batchSize) {
    const batch = applicants.slice(i, i + batchSize);
    
    for (const applicant of batch) {
      let shouldProcess = false;
      
      // Check each dependency field
      for (const inputFieldId of Array.from(dependencyMap.keys())) {
        // If any required field has a value, we need to process this applicant
        const value = applicant.getCellValueAsString(inputFieldId);
        if (value && value.trim() !== "") {
          shouldProcess = true;
          break;
        }
      }
      
      if (shouldProcess) {
        applicantsToProcess.push(applicant);
      } else {
        skippedApplicants.push(applicant);
      }
    }
    
    // Update progress to show the precheck is working
    setProgress(prev => i / applicants.length * 0.1); // Use 10% of progress bar for precheck
  }
  
  return {
    applicantsToProcess,
    skippedApplicants
  };
};

const renderPreviewText = (
  numberOfApplicants: number,
  numberOfEvaluationCriteria: number,
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
  const run = async () => {
    setRunning(true);
    setProgress(0);
    setResult(null);
    console.log("Running preset", preset);
    try {
      if (!applicantTable) throw new Error("Could not access applicant table");
      if (!evaluationTable)
        throw new Error("Could not access evaluation table");
      if (!preset.applicantFields.length)
        throw new Error("No input fields selected");
      if (!preset.evaluationFields.length)
        throw new Error("No output fields selected");
      setResult("Getting applicant records...");
      const applicantView = applicantTable.getViewById(preset.applicantViewId);
      const applicantRecords = await applicantView.selectRecordsAsync();
      setResult(
        renderPreviewText(
          applicantRecords.records.length,
          preset.evaluationFields.length,
        ),
      );
      
      // Fast precheck to eliminate applicants that don't need processing
      setResult(`Starting pre-check for ${applicantRecords.records.length} applicants...`);
      const { applicantsToProcess, skippedApplicants } = await quickPrecheck(
        applicantRecords.records,
        preset,
        setProgress
      );
      
      setResult(`Pre-check complete: ${applicantsToProcess.length} applicants to process, ${skippedApplicants.length} skipped entirely because their dependency fields are empty.`);
      
      if (applicantsToProcess.length === 0) {
        setResult(`No applicants require processing. All ${skippedApplicants.length} applicants had empty dependency fields.`);
        setRunning(false);
        return;
      }
      
      // Process applicants in larger batches for speed
      const batchSize = 10; // Process more applicants at a time for better throughput
      const evaluationPromises = evaluateApplicants(
        applicantsToProcess,
        preset,
        setProgress,
      );

      let successCount = 0;
      let failureCount = 0;
      const failures = [];

      // Process in batches
      for (let i = 0; i < evaluationPromises.length; i += batchSize) {
        const batch = evaluationPromises.slice(i, i + batchSize);
        console.log(
          `Processing batch ${i / batchSize + 1} of ${Math.ceil(evaluationPromises.length / batchSize)}`,
        );

        const batchResults = await Promise.allSettled(
          batch.map(async (evaluationPromise) => {
            try {
              const evaluation = await evaluationPromise;

              // No need to process evaluation anymore as fields with refused ratings
              // have already been filtered out in evaluateApplicant
              const processedEvaluation = { ...evaluation };

              // Minimal logging to reduce overhead
              if (i === 0 && evaluationPromise === batch[0]) {
                console.log(`First evaluation in batch:`, Object.keys(processedEvaluation));
              }

              // More aggressive retry with longer backoff
              return await pRetry(
                () => evaluationTable.createRecordAsync(processedEvaluation),
                {
                  retries: 5,
                  factor: 2,
                  minTimeout: 1000,
                  maxTimeout: 15000,
                  onFailedAttempt: (error) => {
                    console.warn(
                      `Retry attempt failed for applicant ${evaluation[preset.evaluationApplicantField]?.[0]?.id}:`,
                      error,
                    );
                  },
                },
              );
            } catch (error) {
              // Get applicant ID/name for better error reporting
              const applicantId = error.message?.match(/applicant "([^"]+)"/)?.[1] || "unknown";
              // Get field name/ID for better error reporting (field name is now included in the error message)
              const fieldMatch = error.message?.match(/field "([^"]+)"/);
              const fieldNameOrId = fieldMatch?.[1] || "unknown";
              
              console.error(`Failed to process evaluation for applicant "${applicantId}" in field "${fieldNameOrId}":`, error);
              
              // Make error message more user-friendly and add to results
              setResult(prev => {
                // Extract just the error type for a cleaner message
                let errorType = "processing error";
                if (error.message?.includes("Missing final ranking")) {
                  errorType = "missing rating";
                } else if (error.message?.includes("Non-integer final ranking")) {
                  errorType = "invalid rating format";
                }
                
                return `${prev}\n⚠️ Error processing applicant "${applicantId}" in field "${fieldNameOrId}": ${errorType}`;
              });
              
              throw error;
            }
          }),
        );

        // Count successes and failures for this batch
        const batchSuccesses = batchResults.filter(
          (r) => r.status === "fulfilled",
        );
        const batchFailures = batchResults.filter(
          (r) => r.status === "rejected",
        );

        successCount += batchSuccesses.length;
        failureCount += batchFailures.length;
        failures.push(...batchFailures);

        // Update the UI to show progress
        setResult(`Processed ${successCount}/${evaluationPromises.length} applicants (${skippedApplicants.length} skipped entirely)`);
        
        // No delay between batches to maximize throughput
        // If Airtable rate limits become an issue, we can add it back
      }

      // Update the UI with final results
      // Create a more detailed summary message
      let summaryMessage = `Successfully created ${successCount} evaluation(s).`;
      
      if (failureCount > 0) {
        summaryMessage += ` Failed ${failureCount} times.`;
        
        // Extract and display up to 3 unique error types from failures
        const uniqueErrors = new Map();
        failures.forEach(failure => {
          const errorMessage = failure.reason?.message || "Unknown error";
          // Extract field and applicant info if available
          const fieldMatch = errorMessage.match(/field "([^"]+)"/);
          const applicantMatch = errorMessage.match(/applicant "([^"]+)"/);
          
          if (fieldMatch && applicantMatch) {
            // Determine the error type
            let errorType = "other";
            if (errorMessage.includes("Missing final ranking")) {
              errorType = "missing_rating";
            } else if (errorMessage.includes("Non-integer final ranking")) {
              errorType = "invalid_rating";
            }
            
            const key = `${fieldMatch[1]}:${errorType}`;
            if (!uniqueErrors.has(key)) {
              uniqueErrors.set(key, {
                field: fieldMatch[1],
                errorType,
                count: 0
              });
            }
            uniqueErrors.get(key).count++;
          }
        });
        
        // Add summary of most common errors
        if (uniqueErrors.size > 0) {
          summaryMessage += " Common issues:";
          
          Array.from(uniqueErrors.entries())
            .sort((a, b) => b[1].count - a[1].count)
            .slice(0, 3)
            .forEach(([_, info]) => {
              // Get human-readable error message
              let errorDescription = "";
              if (info.errorType === "missing_rating") {
                errorDescription = " (missing rating)";
              } else if (info.errorType === "invalid_rating") {
                errorDescription = " (invalid rating format)";
              }
              summaryMessage += `\n- ${info.count} failures in field "${info.field}"${errorDescription}`;
            });
            
          summaryMessage += "\nSee console logs for complete details.";
        }
      }
      
      setResult(summaryMessage);
    } catch (error) {
      const errorMessage =
        "Error: " + (error instanceof Error ? error.message : String(error));
      setResult(errorMessage);
      setRunning(false);
    }
    setRunning(false);
  };

  return (
    <div className="mb-24">
      <FormField label="Applicant table">
        <TablePickerSynced
          globalConfigKey={["presets", preset.name, "applicantTableId"]}
          onChange={() => {
            globalConfig.setAsync(
              ["presets", preset.name, "applicantViewId"],
              "",
            );
            globalConfig.setAsync(
              ["presets", preset.name, "applicantFields"],
              [],
            );
          }}
        />
      </FormField>
      {applicantTable && (
        <>
          <FormField label="Applicant view">
            <ViewPickerSynced
              globalConfigKey={["presets", preset.name, "applicantViewId"]}
              table={applicantTable}
            />
          </FormField>
          <FormField label="Answer (input) fields">
            <div className="flex flex-col gap-2">
              {preset.applicantFields.map((_, index) => (
                <ApplicantFieldEditor
                  key={index}
                  preset={preset}
                  index={index}
                />
              ))}
              <ApplicantFieldEditor
                key={preset.applicantFields.length}
                preset={preset}
                index={preset.applicantFields.length}
              />
            </div>
          </FormField>
        </>
      )}

      <FormField label="Evaluation table">
        <TablePickerSynced
          globalConfigKey={["presets", preset.name, "evaluationTableId"]}
          onChange={() => {
            globalConfig.setAsync(
              ["presets", preset.name, "evaluationFields"],
              [],
            );
            globalConfig.setAsync(
              ["presets", preset.name, "evaluationLogsField"],
              undefined,
            );
          }}
        />
      </FormField>
      {evaluationTable && (
        <>
          <FormField label="Score (output) fields">
            <div className="flex flex-col gap-2">
              {preset.evaluationFields.map((_, index) => (
                <EvaluationFieldEditor
                  key={index}
                  preset={preset}
                  index={index}
                />
              ))}
              <EvaluationFieldEditor
                key={preset.evaluationFields.length}
                preset={preset}
                index={preset.evaluationFields.length}
              />
            </div>
          </FormField>
          <FormField label="Applicant field">
            <FieldPickerSynced
              allowedTypes={[FieldType.MULTIPLE_RECORD_LINKS]}
              globalConfigKey={[
                "presets",
                preset.name,
                "evaluationApplicantField",
              ]}
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
              globalConfigKey={["presets", preset.name, "evaluationLogsField"]}
              table={evaluationTable}
              shouldAllowPickingNone={true}
            />
          </FormField>
        </>
      )}

      <Button
        // @ts-ignore
        type="[workaround]"
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

const ApplicantFieldEditor: React.FC<FieldEditorProps> = ({
  preset,
  index,
}) => {
  const applicantField = preset.applicantFields[index] ?? { fieldId: "" };

  const base = useBase();
  const applicantTable = base.getTableByIdIfExists(preset.applicantTableId);

  const [field, setField] = useState<Field>(
    applicantTable.getFieldByIdIfExists(applicantField.fieldId),
  );
  const [questionName, setQuestionName] = useState<string>(
    applicantField.questionName ?? "",
  );

  const saveField = (applicantField: Preset["applicantFields"][number]) => {
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
          i === index ? applicantField : original,
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

const EvaluationFieldEditor: React.FC<FieldEditorProps> = ({
  preset,
  index,
}) => {
  const evaluationField = preset.evaluationFields[index] ?? {
    fieldId: "",
    criteria: "",
    dependsOnInputField: undefined,
  };

  const base = useBase();
  const evaluationTable = base.getTableByIdIfExists(preset.evaluationTableId);
  const applicantTable = base.getTableByIdIfExists(preset.applicantTableId);

  const [field, setField] = useState<Field>(
    evaluationTable.getFieldByIdIfExists(evaluationField.fieldId),
  );
  const [criteria, setCriteria] = useState<string>(
    evaluationField.criteria ?? "",
  );
  // We don't use the dependsOnField value directly, but we need the setter
  const [, setDependsOnField] = useState<Field | null>(
    evaluationField.dependsOnInputField
      ? applicantTable?.getFieldByIdIfExists(
          evaluationField.dependsOnInputField,
        )
      : null,
  );

  // Create options for the dependency dropdown from the applicant fields
  const inputFieldOptions = useMemo(() => {
    if (!applicantTable) return [{ value: "", label: "None" }];

    const options = [{ value: "", label: "None (always evaluate)" }];

    preset.applicantFields.forEach(({ fieldId }) => {
      const field = applicantTable.getFieldByIdIfExists(fieldId);
      if (field) {
        options.push({
          value: fieldId,
          label: field.name,
        });
      }
    });

    return options;
  }, [applicantTable, preset.applicantFields]);

  const saveField = (evaluationField: Preset["evaluationFields"][number]) => {
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
          i === index ? evaluationField : original,
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
          value={evaluationField.dependsOnInputField || ""}
          onChange={(value) => {
            const dependsOnInputField = value === "" ? undefined : value;
            setDependsOnField(
              dependsOnInputField
                ? applicantTable?.getFieldByIdIfExists(
                    dependsOnInputField as string,
                  )
                : null,
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
