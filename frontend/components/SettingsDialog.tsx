import { Button, Dialog, FormField, Heading, Input, Select } from '@airtable/blocks/ui';
import React, { useState, useEffect } from 'react';
import { globalConfig } from '@airtable/blocks';
import { 
  MODEL_PROVIDERS, 
  OPENAI_MODELS, 
  ANTHROPIC_MODELS,
  DEFAULT_OPENAI_MODEL,
  DEFAULT_ANTHROPIC_MODEL
} from '../../lib/models/config';

// Convert the model providers to options for select dropdown
const MODEL_PROVIDER_OPTIONS = MODEL_PROVIDERS.map(provider => ({
  label: `${provider.emoji} ${provider.name}`,
  value: provider.id,
}));

// Convert the models to options for select dropdowns
const OPENAI_MODEL_OPTIONS = OPENAI_MODELS.filter(model => model.isAvailable).map(model => ({
  label: `${model.emoji} ${model.label}`,
  value: model.value,
}));

const ANTHROPIC_MODEL_OPTIONS = ANTHROPIC_MODELS.filter(model => model.isAvailable).map(model => ({
  label: `${model.emoji} ${model.label}`,
  value: model.value,
}));

export const SettingsDialog = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const [openAiKey, setOpenAiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('openai');
  const [openAiModel, setOpenAiModel] = useState(DEFAULT_OPENAI_MODEL);
  const [anthropicModel, setAnthropicModel] = useState(DEFAULT_ANTHROPIC_MODEL);
  
  useEffect(() => {
    // Load existing settings from global config if available
    const storedOpenAiKey = globalConfig.get('openAiApiKey') as string || '';
    const storedAnthropicKey = globalConfig.get('anthropicApiKey') as string || '';
    const storedSelectedModel = globalConfig.get('selectedModel') as string || 'openai';
    const storedOpenAiModel = globalConfig.get('openAiModel') as string || DEFAULT_OPENAI_MODEL;
    const storedAnthropicModel = globalConfig.get('anthropicModel') as string || DEFAULT_ANTHROPIC_MODEL;
    
    setOpenAiKey(storedOpenAiKey);
    setAnthropicKey(storedAnthropicKey);
    setSelectedModel(storedSelectedModel);
    setOpenAiModel(storedOpenAiModel);
    setAnthropicModel(storedAnthropicModel);
  }, [isOpen]);
  
  const handleSave = async () => {
    try {
      await globalConfig.setAsync('openAiApiKey', openAiKey);
      await globalConfig.setAsync('anthropicApiKey', anthropicKey);
      await globalConfig.setAsync('selectedModel', selectedModel);
      await globalConfig.setAsync('openAiModel', openAiModel);
      await globalConfig.setAsync('anthropicModel', anthropicModel);
      
      onClose();
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  };
  
  // Find the selected model to display its description
  const getModelDescription = (modelId: string, provider: 'openai' | 'anthropic') => {
    const models = provider === 'openai' ? OPENAI_MODELS : ANTHROPIC_MODELS;
    const model = models.find(m => m.value === modelId);
    return model?.description || '';
  };
  
  if (!isOpen) return null;
  
  return (
    <Dialog onClose={onClose} width="500px">
      <Dialog.CloseButton />
      <Heading>AI Model Settings</Heading>
      
      <div className="my-4">
        <FormField label="AI Model Provider">
          <Select
            options={MODEL_PROVIDER_OPTIONS}
            value={selectedModel}
            onChange={value => setSelectedModel(value as string)}
          />
        </FormField>
        
        <div className="p-2 mt-2 bg-gray-100 rounded">
          <FormField label="OpenAI Settings">
            <div className="mb-2">
              <FormField label="API Key" className="mb-2">
                <Input
                  value={openAiKey}
                  onChange={e => setOpenAiKey(e.target.value)}
                  placeholder="sk-..."
                  type="password"
                />
              </FormField>
              <FormField label="Model">
                <Select
                  options={OPENAI_MODEL_OPTIONS}
                  value={openAiModel}
                  onChange={value => setOpenAiModel(value as string)}
                />
                <div className="mt-1 text-xs text-gray-500">
                  {getModelDescription(openAiModel, 'openai')}
                </div>
              </FormField>
            </div>
          </FormField>
        </div>
        
        <div className="p-2 mt-2 bg-gray-100 rounded">
          <FormField label="Anthropic Settings">
            <div className="mb-2">
              <FormField label="API Key" className="mb-2">
                <Input
                  value={anthropicKey}
                  onChange={e => setAnthropicKey(e.target.value)}
                  placeholder="sk-ant-api..."
                  type="password"
                />
              </FormField>
              <FormField label="Model">
                <Select
                  options={ANTHROPIC_MODEL_OPTIONS}
                  value={anthropicModel}
                  onChange={value => setAnthropicModel(value as string)}
                />
                <div className="mt-1 text-xs text-gray-500">
                  {getModelDescription(anthropicModel, 'anthropic')}
                </div>
              </FormField>
            </div>
          </FormField>
        </div>
      </div>
      
      <div className="flex justify-end space-x-2">
        <Button variant="default" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="primary" onClick={handleSave}>
          Save
        </Button>
      </div>
    </Dialog>
  );
}; 