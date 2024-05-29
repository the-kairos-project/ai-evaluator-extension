import {
  Button,
  Dialog,
  FormField,
  Heading,
  Input,
  Select,
} from "@airtable/blocks/ui";
import React, { useMemo, useState } from "react";
import { defaultPreset, deletePreset, getPresets, getSelectedPreset, selectPreset, upsertPreset, useSelectedPreset } from "../../lib/preset";

const PresetChooser = () => {
  const selectedPreset = getSelectedPreset();
  const presets = getPresets();

  const presetOptions = useMemo(() => {
    if (!presets) return [];
    else
      return presets.map((preset) => ({
        label: preset.name,
        value: preset.name,
      }));
  }, [presets]);

  const [newPresetDialogOpen, setNewPresetDialogOpen] = useState(false);
  const [newPresetName, setNewPresetName] = useState("");

  const closeNewPresetDialog = () => {
    setNewPresetDialogOpen(false);
    setNewPresetName("");
  };

  const [, forceUpdate] = useState(0);

  return (
    <div className="flex items-center">
      <span className="hidden sm:block mr-2">Preset:</span>
      <div>
        <Select
          className="min-w-[5rem] rounded-r-none"
          options={[
            ...(presetOptions || []),
            { label: "+ Create new preset", value: "new" },
          ]}
          value={selectedPreset.name}
          onChange={(value) => {
            if (value === "new") {
              setNewPresetDialogOpen(true);
            } else {
              selectPreset(value as string);
            }
          }}
          size="small"
        />
        {newPresetDialogOpen && (
          <Dialog onClose={() => closeNewPresetDialog()} width="320px">
            <Dialog.CloseButton />
            <Heading>Create new preset</Heading>
            <FormField label="Name">
              <Input
                autoFocus={true}
                value={newPresetName}
                onChange={(e) => setNewPresetName(e.target.value)}
              />
            </FormField>
            <div className="flex w-full justify-end">
              <Button
                onClick={() => {
                  closeNewPresetDialog();
                  upsertPreset({ ...defaultPreset, name: newPresetName })
                  selectPreset(newPresetName);
                  forceUpdate(Date.now());
                }}
              >
                Create
              </Button>
            </div>
          </Dialog>
        )}
      </div>
    </div>
  );
};

export const PresetManager = () => {
  const selectedPreset = useSelectedPreset();
  const [editPresetDialogOpen, setEditPresetDialogOpen] = useState(false);
  const [editPresetName, setEditPresetName] = useState(selectedPreset.name);
  const [editPresetJson, setEditPresetJson] = useState(JSON.stringify(selectedPreset));
  const openEditPresetDialog = () => {
    setEditPresetName(selectedPreset.name);
    setEditPresetJson(JSON.stringify(selectedPreset));
    setEditPresetDialogOpen(true);
  }
  const closeEditPresetDialog = () => {
    setEditPresetDialogOpen(false);
  };

  const showDeletePreset = getPresets().length > 1;

  return (
    <div className="flex text-slate-50">
      <PresetChooser />
      <Button
        icon="edit"
        className={`bg-slate-200 text-slate-700 h-7 rounded-l-none border-solid border border-y-0 border-r-0 ${showDeletePreset ? "rounded-none" : ""}`}
        onClick={() => openEditPresetDialog()}
        aria-label="Edit preset"
      ></Button>
      {showDeletePreset && (
        <Button
          icon="trash"
          className="bg-slate-200 text-slate-700 h-7 rounded-l-none border-solid border border-y-0 border-r-0 border-slate-700"
          onClick={async () => {
            closeEditPresetDialog();
            deletePreset(selectedPreset.name);
          }}
          aria-label="Delete preset"
        ></Button>
      )}
      {editPresetDialogOpen && (
        <Dialog onClose={closeEditPresetDialog} width="320px">
          <Dialog.CloseButton />
          <div className="flex">
            <Heading>Edit preset</Heading>
          </div>
          <FormField label="Name">
            <Input
              autoFocus={true}
              value={editPresetName}
              onChange={(e) => setEditPresetName(e.target.value)}
            />
          </FormField>
          <FormField label="(advanced) Overwrite JSON">
            <Input
              autoFocus={true}
              value={editPresetJson}
              onChange={(e) => setEditPresetJson(e.target.value)}
            />
          </FormField>
          <div className="flex w-full justify-end">
            <Button
              onClick={() => {
                closeEditPresetDialog();
                if (editPresetJson) {
                  upsertPreset({ ...JSON.parse(editPresetJson), name: editPresetName }, selectedPreset.name)
                } else {
                  upsertPreset({ ...selectedPreset, name: editPresetName }, selectedPreset.name)
                }
              }}
            >
              Save
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  )
}