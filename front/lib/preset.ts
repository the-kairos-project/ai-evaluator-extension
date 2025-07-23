import { globalConfig } from '@airtable/blocks';
import { useGlobalConfig } from '@airtable/blocks/ui';

export type Preset = {
  name: string;

  applicantTableId: string;
  applicantViewId: string;
  applicantFields: { fieldId: string; questionName?: string }[];

  evaluationTableId: string;
  evaluationFields: {
    fieldId: string;
    criteria: string;
    dependsOnInputField?: string; // Optional field ID from the applicant fields that must be non-empty
  }[];
  evaluationApplicantField: string;
  evaluationLogsField?: string;
  
  // LinkedIn enrichment options
  useLinkedinEnrichment?: boolean; // Whether to use LinkedIn enrichment
  linkedinUrlField?: string; // Field ID containing LinkedIn URLs
  linkedinDataField?: string; // Field ID to store LinkedIn data output
  
  // PDF resume enrichment options
  usePdfResumeEnrichment?: boolean; // Whether to use PDF resume enrichment
  pdfResumeField?: string; // Field ID containing PDF resume URLs or attachments
  pdfResumeDataField?: string; // Field ID to store PDF resume data output
  
  // Multi-axis evaluation options
  useMultiAxisEvaluation?: boolean; // Whether to use multi-axis evaluation
  multiAxisDataField?: string; // Field ID to store multi-axis evaluation data
  
  // Individual axis output fields
  generalPromiseField?: string; // Field ID to store General Promise axis score
  mlSkillsField?: string; // Field ID to store ML Skills axis score
  softwareEngineeringField?: string; // Field ID to store Software Engineering Skills axis score
  policyExperienceField?: string; // Field ID to store Policy Experience axis score
  aiSafetyUnderstandingField?: string; // Field ID to store Understanding of AI Safety axis score
  pathToImpactField?: string; // Field ID to store Path to Impact axis score
  researchExperienceField?: string; // Field ID to store Research Experience axis score
};

export const defaultPreset: Preset = {
  name: 'New preset',

  applicantTableId: 'tblXKnWoXK3R63F6D',
  applicantViewId: '',
  applicantFields: [],

  evaluationTableId: 'tblqqU2PPOCeRbQoj',
  evaluationFields: [],
  evaluationApplicantField: 'fldAVaTU0Btgt1i3p',
  evaluationLogsField: undefined,
  
  // LinkedIn enrichment options (disabled by default)
  useLinkedinEnrichment: false,
  linkedinUrlField: undefined,
  linkedinDataField: undefined,
  
  // PDF resume enrichment options (disabled by default)
  usePdfResumeEnrichment: false,
  pdfResumeField: undefined,
  pdfResumeDataField: undefined,
  
  // Multi-axis evaluation options (disabled by default)
  useMultiAxisEvaluation: false,
  multiAxisDataField: undefined,
  
  // Individual axis output fields (undefined by default)
  generalPromiseField: undefined,
  mlSkillsField: undefined,
  softwareEngineeringField: undefined,
  policyExperienceField: undefined,
  aiSafetyUnderstandingField: undefined,
  pathToImpactField: undefined,
  researchExperienceField: undefined
};

export const upsertPreset = async (
  preset: Preset = defaultPreset,
  oldName: string = preset.name
): Promise<Preset> => {
  if (preset.name !== oldName) {
    globalConfig.setAsync(['presets', oldName], undefined);

    const selectedPresetName = globalConfig.get('selectedPresetName');
    if (selectedPresetName === oldName) {
      globalConfig.setAsync(['selectedPresetName'], preset.name);
    }
  }
  globalConfig.setAsync(['presets', preset.name], preset);
  return preset;
};

export const deletePreset = async (name: string): Promise<void> => {
  await Promise.all([
    globalConfig.setAsync(['presets', name], undefined),
    globalConfig.setAsync(['selectedPresetName'], getPresets()[0].name),
  ]);
};

export const selectPreset = async (name: string): Promise<void> => {
  return globalConfig.setAsync(['selectedPresetName'], name);
};

export const getPresets = (): Preset[] => {
  const presetsObj = globalConfig.get(['presets']);
  if (presetsObj === undefined) {
    return [getSelectedPreset()];
  }

  return Object.values(presetsObj);
};

export const getSelectedPreset = (): Preset => {
  const selectedPresetName = globalConfig.get('selectedPresetName');
  const selectedPreset = globalConfig.get([
    'presets',
    (selectedPresetName as string | undefined) || 'New preset',
  ]);

  if (!selectedPreset) {
    const newPreset = { ...defaultPreset };
    upsertPreset(newPreset);
    selectPreset(newPreset.name);
    return newPreset;
  }

  return selectedPreset as Preset;
};

export const useSelectedPreset = (): Preset => {
  useGlobalConfig();
  return getSelectedPreset();
};
