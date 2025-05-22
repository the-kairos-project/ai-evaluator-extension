import { Icon, FormField } from '@airtable/blocks/ui';
import React, { useState } from 'react';
import { globalConfig } from '@airtable/blocks';
import { HelpContent, HELP_CONTENT } from './helpContent';

// Enhanced tooltip with special handling for bottom fields
interface TooltipProps {
  content: HelpContent;
  icon?: 'help' | 'info';
  helpKey?: keyof typeof HELP_CONTENT;
}

export const Tooltip: React.FC<TooltipProps> = ({ content, icon = 'info', helpKey }) => {
  const [isVisible, setIsVisible] = useState(false);
  const buttonRef = React.useRef<HTMLButtonElement>(null);

  // Fields that need special positioning
  const isLogsField = helpKey === 'logsField';
  const isApplicantField = helpKey === 'applicantField';

  const handleShow = () => {
    setIsVisible(true);
  };

  const handleHide = () => {
    setIsVisible(false);
  };

  return (
    <div className="relative inline-block ml-1">
      <button
        ref={buttonRef}
        type="button"
        className="text-gray-400 hover:text-gray-600 focus:outline-none"
        onMouseEnter={handleShow}
        onMouseLeave={handleHide}
        onClick={() => isVisible ? handleHide() : handleShow()}
        aria-label="Show help"
      >
        <Icon name={icon} size={14} />
      </button>
      
      {isVisible && (
        <div 
          className={`absolute z-50 w-80 p-3 bg-white border rounded-lg shadow-lg ${
            (isLogsField || isApplicantField)
              ? 'bottom-6 left-6'
              : 'top-6 left-6'
          }`}
          style={{
            maxWidth: '320px',
            // Positioning logic for different field types
            ...((isLogsField || isApplicantField) ? {
              // Position to the left above for both bottom fields
              bottom: '32px',
              left: '24px',
              transform: 'translateX(0)',
              right: 'auto'
            } : {
              // Regular positioning for other fields  
              left: '24px',
              right: 'auto',
              top: '32px',
              transform: buttonRef.current && 
                (buttonRef.current.getBoundingClientRect().left + 320 > window.innerWidth) 
                ? 'translateX(-280px)' : 'translateX(0)'
            })
          }}
        >
          <div className="text-sm">
            <div className="font-medium text-gray-900 mb-2">
              {content.purpose}
            </div>
            
            {content.setup && (
              <div className="mb-2">
                <span className="font-medium text-gray-700">Setup: </span>
                <span className="text-gray-600">{content.setup}</span>
              </div>
            )}
            
            {content.examples && content.examples.length > 0 && (
              <div className="mb-2">
                <span className="font-medium text-gray-700">Examples:</span>
                <ul className="mt-1 ml-4 list-disc">
                  {content.examples.map((example, index) => (
                    <li key={index} className="text-gray-600 text-xs">{example}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {content.bestPractices && content.bestPractices.length > 0 && (
              <div className="mb-2">
                <span className="font-medium text-gray-700">Best Practices:</span>
                <ul className="mt-1 ml-4 list-disc">
                  {content.bestPractices.map((practice, index) => (
                    <li key={index} className="text-gray-600 text-xs">{practice}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {content.consequences && (
              <div className="text-xs text-orange-700 bg-orange-50 p-2 rounded mt-2">
                <span className="font-medium">Important: </span>
                {content.consequences}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Guided mode expanded help component
interface GuidedHelpProps {
  content: HelpContent;
}

export const GuidedHelp: React.FC<GuidedHelpProps> = ({ content }) => {
  return (
    <div className="mt-2 p-3 bg-blue-50 rounded border-l-4 border-blue-400">
      <div className="text-sm">
        <div className="text-blue-900 mb-2">
          📝 <strong>Purpose:</strong> {content.purpose}
        </div>
        
        {content.setup && (
          <div className="text-blue-800 mb-2">
            🔧 <strong>Setup:</strong> {content.setup}
          </div>
        )}
        
        {content.examples && content.examples.length > 0 && (
          <div className="mb-2">
            <div className="text-blue-800 font-medium">💡 Examples:</div>
            <ul className="mt-1 ml-4 list-disc">
              {content.examples.map((example, index) => (
                <li key={index} className="text-blue-700 text-xs">{example}</li>
              ))}
            </ul>
          </div>
        )}
        
        {content.bestPractices && content.bestPractices.length > 0 && (
          <div className="mb-2">
            <div className="text-blue-800 font-medium">✨ Best Practices:</div>
            <ul className="mt-1 ml-4 list-disc">
              {content.bestPractices.map((practice, index) => (
                <li key={index} className="text-blue-700 text-xs">{practice}</li>
              ))}
            </ul>
          </div>
        )}
        
        {content.consequences && (
          <div className="text-orange-800 bg-orange-100 p-2 rounded mt-2 text-xs">
            ⚠️ <strong>Important:</strong> {content.consequences}
          </div>
        )}
      </div>
    </div>
  );
};

// Helper component to create FormField with tooltip
interface FormFieldWithTooltipProps {
  label: string;
  helpKey: keyof typeof HELP_CONTENT;
  showGuidedHelp?: boolean;
  className?: string;
  children: React.ReactNode;
}

export const FormFieldWithTooltip: React.FC<FormFieldWithTooltipProps> = ({
  label,
  helpKey,
  showGuidedHelp = false,
  className,
  children
}) => {
  const helpContent = HELP_CONTENT[helpKey];
  
  return (
    <div>
      <FormField 
        label={
          <div className="flex items-center">
            {label}
            <Tooltip content={helpContent} helpKey={helpKey} />
          </div>
        } 
        className={className}
      >
        {children}
      </FormField>
      {showGuidedHelp && <GuidedHelp content={helpContent} />}
    </div>
  );
};

// Utility to check if guided mode is enabled
export const useGuidedMode = (): boolean => {
  return globalConfig.get('showDetailedHelp') as boolean || false;
}; 