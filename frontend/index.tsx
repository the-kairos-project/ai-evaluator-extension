import { Icon, initializeBlock, loadScriptFromURLAsync } from '@airtable/blocks/ui';
import { Tab } from '@headlessui/react';
import React, { Fragment, useState } from 'react';
import type { IconName } from '@airtable/blocks/dist/types/src/ui/icon_config';
import { PresetManager } from './components/PresetManager';
import { MainPage } from './MainPage';
import { SettingsDialog } from './components/SettingsDialog';

const MyTabLink = ({ icon, label }: { icon: IconName; label: string }) => {
  return (
    <Tab as={Fragment}>
      {({ selected }) => (
        <button
          type="button"
          className={
            `flex px-2 py-1 ${selected ? 'text-slate-50' : 'text-slate-400'}`
          }
        >
          <Icon name={icon} size={16} />
          <span className="ml-1 tracking-widest uppercase text-xs font-medium">
            {label}
          </span>
        </button>
      )}
    </Tab>
  );
};

function App() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  
  const openSettings = () => {
    setSettingsOpen(true);
  };
  
  const closeSettings = () => {
    setSettingsOpen(false);
  };

  return (
    <main className="bg-slate-50 h-full">
      <Tab.Group>
        <Tab.List className="p-1 w-auto flex gap-2 sm:gap-4 overflow-x-auto items-center justify-between bg-slate-500">
          <div className="flex items-center">
            <MyTabLink icon="aiAssistant" label="AI Evaluator" />
          </div>
          <div className="flex items-center">
            <PresetManager />
            <button
              onClick={openSettings}
              className="ml-2 bg-slate-200 text-slate-700 h-7 px-2 rounded flex items-center"
              aria-label="Settings"
            >
              <Icon name="settings" size={14} className="mr-1" />
              <span className="text-xs">Settings</span>
            </button>
          </div>
        </Tab.List>
        <Tab.Panels className="p-3 sm:p-4">
          <Tab.Panel>
            <MainPage />
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
      
      <SettingsDialog isOpen={settingsOpen} onClose={closeSettings} />
    </main>
  );
}

// Note: The ReactDOM.render warning is coming from Airtable's initializeBlock function
// We can't easily fix it since it's using the legacy API internally
// When Airtable updates their SDK, this warning should disappear
loadScriptFromURLAsync('https://cdn.tailwindcss.com').then(async () => {
  initializeBlock(() => <App />);
});
