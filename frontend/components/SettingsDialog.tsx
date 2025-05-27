import { globalConfig } from '@airtable/blocks';
import {
  Button,
  Dialog,
  FormField,
  Heading,
  Input,
  Select,
  Switch,
} from '@airtable/blocks/ui';
import React, { useState, useEffect } from 'react';
import {
  CONCURRENCY_OPTIONS,
  DEFAULT_CONCURRENCY,
  getCurrentConcurrency,
  saveConcurrency,
} from '../../lib/concurrency/config';
import {
  ANTHROPIC_MODELS,
  DEFAULT_ANTHROPIC_MODEL,
  DEFAULT_OPENAI_MODEL,
  MODEL_PROVIDERS,
  OPENAI_MODELS,
} from '../../lib/models/config';
import {
  ACADEMIC_TEMPLATE,
  AVAILABLE_TEMPLATES,
  getPromptSettings,
  savePromptSettings,
} from '../../lib/prompts';

// Convert the model providers to options for select dropdown
const MODEL_PROVIDER_OPTIONS = MODEL_PROVIDERS.map((provider) => ({
  label: `${provider.emoji} ${provider.name}`,
  value: provider.id,
}));

// Convert the models to options for select dropdowns
const OPENAI_MODEL_OPTIONS = OPENAI_MODELS.filter((model) => model.isAvailable).map(
  (model) => ({
    label: `${model.emoji} ${model.label}`,
    value: model.value,
  })
);

const ANTHROPIC_MODEL_OPTIONS = ANTHROPIC_MODELS.filter(
  (model) => model.isAvailable
).map((model) => ({
  label: `${model.emoji} ${model.label}`,
  value: model.value,
}));

// Convert templates to options for select dropdown
const TEMPLATE_OPTIONS = AVAILABLE_TEMPLATES.map((template) => ({
  label: template.name,
  value: template.id,
}));

// Convert concurrency options to select dropdown options
const CONCURRENCY_SELECT_OPTIONS = CONCURRENCY_OPTIONS.map((option) => ({
  label: option.label,
  value: option.value.toString(),
}));

export const SettingsDialog = ({
  isOpen,
  onClose,
}: { isOpen: boolean; onClose: () => void }) => {
  const [openAiKey, setOpenAiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('openai');
  const [openAiModel, setOpenAiModel] = useState(DEFAULT_OPENAI_MODEL);
  const [anthropicModel, setAnthropicModel] = useState(DEFAULT_ANTHROPIC_MODEL);
  const [showDetailedHelp, setShowDetailedHelp] = useState(false);

  // Prompt settings state
  const [selectedTemplate, setSelectedTemplate] = useState(ACADEMIC_TEMPLATE.id);
  const [customPrompt, setCustomPrompt] = useState('');
  const [rankingKeyword, setRankingKeyword] = useState(
    ACADEMIC_TEMPLATE.rankingKeyword
  );
  const [additionalInstructions, setAdditionalInstructions] = useState('');

  // Cost estimation settings
  const [preferredCurrency, setPreferredCurrency] = useState('USD');

  // Concurrency settings
  const [apiConcurrency, setApiConcurrency] = useState(DEFAULT_CONCURRENCY);

  useEffect(() => {
    // Load existing settings from global config if available
    const storedOpenAiKey = (globalConfig.get('openAiApiKey') as string) || '';
    const storedAnthropicKey = (globalConfig.get('anthropicApiKey') as string) || '';
    const storedSelectedModel =
      (globalConfig.get('selectedModel') as string) || 'openai';
    const storedOpenAiModel =
      (globalConfig.get('openAiModel') as string) || DEFAULT_OPENAI_MODEL;
    const storedAnthropicModel =
      (globalConfig.get('anthropicModel') as string) || DEFAULT_ANTHROPIC_MODEL;
    const storedShowDetailedHelp =
      (globalConfig.get('showDetailedHelp') as boolean) || false;

    // Load prompt settings
    const promptSettings = getPromptSettings();

    setOpenAiKey(storedOpenAiKey);
    setAnthropicKey(storedAnthropicKey);
    setSelectedModel(storedSelectedModel);
    setOpenAiModel(storedOpenAiModel);
    setAnthropicModel(storedAnthropicModel);
    setShowDetailedHelp(storedShowDetailedHelp);

    // Set prompt settings
    setSelectedTemplate(promptSettings.selectedTemplate);
    setCustomPrompt(promptSettings.customTemplate?.systemMessage || '');
    setRankingKeyword(promptSettings.rankingKeyword);
    setAdditionalInstructions(promptSettings.additionalInstructions);

    // Load currency preference
    const storedCurrency = (globalConfig.get('preferredCurrency') as string) || 'USD';
    setPreferredCurrency(storedCurrency);

    // Load concurrency setting
    const storedConcurrency = getCurrentConcurrency();
    setApiConcurrency(storedConcurrency);
  }, []);

  const handleSave = async () => {
    try {
      await globalConfig.setAsync('openAiApiKey', openAiKey);
      await globalConfig.setAsync('anthropicApiKey', anthropicKey);
      await globalConfig.setAsync('selectedModel', selectedModel);
      await globalConfig.setAsync('openAiModel', openAiModel);
      await globalConfig.setAsync('anthropicModel', anthropicModel);
      await globalConfig.setAsync('showDetailedHelp', showDetailedHelp);

      // Save currency preference
      await globalConfig.setAsync('preferredCurrency', preferredCurrency);

      // Save concurrency setting
      await saveConcurrency(apiConcurrency);

      // Save prompt settings
      await savePromptSettings({
        selectedTemplate,
        customTemplate: customPrompt
          ? {
              id: 'custom',
              name: 'Custom Template',
              description: 'User-defined custom prompt template',
              systemMessage: customPrompt,
              rankingKeyword: rankingKeyword,
            }
          : null,
        rankingKeyword,
        additionalInstructions,
      });

      onClose();
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  };

  // Find the selected model to display its description
  const getModelDescription = (modelId: string, provider: 'openai' | 'anthropic') => {
    const models = provider === 'openai' ? OPENAI_MODELS : ANTHROPIC_MODELS;
    const model = models.find((m) => m.value === modelId);
    return model?.description || '';
  };

  if (!isOpen) return null;

  return (
    <Dialog onClose={onClose} width="600px">
      <Dialog.CloseButton />
      <Heading>AI Evaluation Settings</Heading>

      <div className="my-4">
        <FormField label="AI Model Provider">
          <Select
            options={MODEL_PROVIDER_OPTIONS}
            value={selectedModel}
            onChange={(value) => setSelectedModel(value as string)}
          />
        </FormField>

        <div className="p-2 mt-2 bg-gray-100 rounded">
          <FormField label="OpenAI Settings">
            <div className="mb-2">
              <FormField label="API Key" className="mb-2">
                <Input
                  value={openAiKey}
                  onChange={(e) => setOpenAiKey(e.target.value)}
                  placeholder="sk-..."
                  type="password"
                />
              </FormField>
              <FormField label="Model">
                <Select
                  options={OPENAI_MODEL_OPTIONS}
                  value={openAiModel}
                  onChange={(value) => setOpenAiModel(value as string)}
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
                  onChange={(e) => setAnthropicKey(e.target.value)}
                  placeholder="sk-ant-api..."
                  type="password"
                />
              </FormField>
              <FormField label="Model">
                <Select
                  options={ANTHROPIC_MODEL_OPTIONS}
                  value={anthropicModel}
                  onChange={(value) => setAnthropicModel(value as string)}
                />
                <div className="mt-1 text-xs text-gray-500">
                  {getModelDescription(anthropicModel, 'anthropic')}
                </div>
              </FormField>
            </div>
          </FormField>
        </div>
      </div>

      <div className="mt-4 p-3 bg-blue-50 rounded">
        <FormField label="Prompt Settings">
          <div className="mb-3">
            <FormField label="Template" className="mb-2">
              <Select
                options={[...TEMPLATE_OPTIONS, { label: 'Custom', value: 'custom' }]}
                value={customPrompt ? 'custom' : selectedTemplate}
                onChange={(value) => {
                  if (value === 'custom') {
                    const template =
                      AVAILABLE_TEMPLATES.find((t) => t.id === selectedTemplate) ||
                      ACADEMIC_TEMPLATE;
                    setCustomPrompt(template.systemMessage);
                  } else {
                    setSelectedTemplate(value as string);
                    setCustomPrompt('');
                  }
                }}
              />
              <div className="mt-1 text-xs text-gray-500">
                {customPrompt
                  ? 'Using custom template'
                  : 'Using standard academic template'}
              </div>
            </FormField>

            {customPrompt && (
              <FormField label="Custom Prompt Template" className="mb-2">
                <textarea
                  className="w-full h-32 p-2 border border-gray-300 rounded text-sm font-mono"
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Enter your custom prompt template..."
                />
                <div className="mt-1 text-xs text-gray-500">
                  <div className="font-medium mb-1">
                    Required placeholders (automatically replaced):
                  </div>
                  <div>
                    • <code>{'{criteriaString}'}</code> → Your evaluation criteria from
                    field configuration
                  </div>
                  <div>
                    • <code>{'{rankingKeyword}'}</code> → The keyword for final score
                    (e.g., FINAL_RANKING, SCORE)
                  </div>
                  <div>
                    • <code>{'{additionalInstructions}'}</code> → Extra instructions
                    from field below (optional)
                  </div>
                </div>
              </FormField>
            )}

            <FormField label="Ranking Keyword" className="mb-2">
              <Input
                value={rankingKeyword}
                onChange={(e) => setRankingKeyword(e.target.value)}
                placeholder="FINAL_RANKING"
              />
              <div className="mt-1 text-xs text-gray-500">
                The keyword the AI should use to output the final score (e.g.,
                FINAL_RANKING, SCORE, RATING)
              </div>
            </FormField>

            <FormField label="Additional Instructions" className="mb-2">
              <textarea
                className="w-full h-20 p-2 border border-gray-300 rounded text-sm"
                value={additionalInstructions}
                onChange={(e) => setAdditionalInstructions(e.target.value)}
                placeholder="Optional extra instructions for the AI evaluator..."
              />
              <div className="mt-1 text-xs text-gray-500">
                Extra guidance that will be appended to the prompt
              </div>
            </FormField>
          </div>
        </FormField>
      </div>

      <div className="mt-4 p-3 bg-gray-50 rounded">
        <FormField label="Interface Options">
          <div className="mb-3">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="font-medium text-sm">Show detailed help</div>
                <div className="text-xs text-gray-500">
                  Display expanded guidance under all configuration fields
                </div>
              </div>
              <Switch
                value={showDetailedHelp}
                onChange={setShowDetailedHelp}
                width={44}
                backgroundColor={showDetailedHelp ? '#3b82f6' : '#d1d5db'}
              />
            </div>

            <FormField label="Preferred Currency for Cost Estimates" className="mb-2">
              <Select
                options={[
                  { label: '$ USD (US Dollar)', value: 'USD' },
                  { label: '£ GBP (British Pound)', value: 'GBP' },
                  { label: '€ EUR (Euro)', value: 'EUR' },
                  { label: 'C$ CAD (Canadian Dollar)', value: 'CAD' },
                ]}
                value={preferredCurrency}
                onChange={(value) => setPreferredCurrency(value as string)}
              />
              <div className="mt-1 text-xs text-gray-500">
                Currency for displaying cost estimates (rates are approximate)
              </div>
            </FormField>

            <FormField label="API Concurrency" className="mb-2">
              <Select
                options={CONCURRENCY_SELECT_OPTIONS}
                value={apiConcurrency.toString()}
                onChange={(value) =>
                  setApiConcurrency(Number.parseInt(value as string))
                }
              />
              <div className="mt-1 text-xs text-gray-500">
                Number of simultaneous API calls. Higher values are faster but may hit
                rate limits.
              </div>
            </FormField>
          </div>
        </FormField>
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
