import { Icon, initializeBlock, loadScriptFromURLAsync } from '@airtable/blocks/ui';
import { Tab } from '@headlessui/react';
import React, { Fragment } from 'react';
import type { IconName } from '@airtable/blocks/dist/types/src/ui/icon_config';
import { PresetManager } from './components/PresetManager';
import { MainPage } from './MainPage';

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
  return (
    <main className="bg-slate-50 min-h-screen">
      <Tab.Group>
        <Tab.List className="p-1 w-auto flex gap-2 sm:gap-4 overflow-x-auto items-center justify-between bg-slate-500">
          <div className="flex items-center">
            <MyTabLink icon="aiAssistant" label="AI Evaluator" />
          </div>
          <PresetManager />
        </Tab.List>
        <Tab.Panels className="p-4 sm:p-6">
          <Tab.Panel>
            <MainPage />
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
    </main>
  );
}

loadScriptFromURLAsync('https://cdn.tailwindcss.com').then(async () => {
  initializeBlock(() => <App />);
});
