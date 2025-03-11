import { globalConfig } from "@airtable/blocks";
import { useGlobalConfig } from "@airtable/blocks/ui";

export type Preset = {
    name: string;

    applicantTableId: string;
    applicantViewId: string;
    applicantFields: { fieldId: string, questionName?: string }[];

    evaluationTableId: string;
    evaluationFields: { 
        fieldId: string, 
        criteria: string,
        dependsOnInputField?: string  // Optional field ID from the applicant fields that must be non-empty
    }[];
    evaluationApplicantField: string;
    evaluationLogsField?: string;
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
};

export const upsertPreset = async (preset: Preset = defaultPreset, oldName: string = preset.name): Promise<Preset> => {
    if (preset.name !== oldName) {
        globalConfig.setAsync(
            ["presets", oldName],
            undefined
        )

        const selectedPresetName = globalConfig.get("selectedPresetName")
        if (selectedPresetName === oldName) {
            globalConfig.setAsync(
                ["selectedPresetName"],
                preset.name
            )
        }
    }
    globalConfig.setAsync(
        ["presets", preset.name],
        preset
    );
    return preset;
};

export const deletePreset = async (name: string): Promise<void> => {
    await Promise.all([
        globalConfig.setAsync(
            ["presets", name],
            undefined
        ),
        globalConfig.setAsync(
            ["selectedPresetName"],
            getPresets()[0].name
        ),
    ])
}

export const selectPreset = async (name: string): Promise<void> => {
    return globalConfig.setAsync(["selectedPresetName"], name)
}

export const getPresets = (): Preset[] => {
    const presetsObj = globalConfig.get(["presets"]);
    if (presetsObj === undefined) {
        return [getSelectedPreset()]
    }

    return Object.values(presetsObj)
}

export const getSelectedPreset = (): Preset => {
    const selectedPresetName = globalConfig.get("selectedPresetName")
    const selectedPreset = globalConfig.get(["presets", (selectedPresetName as string | undefined) || 'New preset']);

    if (!selectedPreset) {
        const newPreset = { ...defaultPreset }
        upsertPreset(newPreset)
        selectPreset(newPreset.name);
        return newPreset;
    }

    return selectedPreset as Preset;
}

export const useSelectedPreset = (): Preset => {
    useGlobalConfig();
    return getSelectedPreset();
}