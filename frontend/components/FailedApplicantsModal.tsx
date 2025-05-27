import { Button, Dialog, Heading, Text } from '@airtable/blocks/ui';
import React from 'react';
import type { FailedApplicant } from '../../lib/failedApplicants';

interface FailedApplicantsModalProps {
  failedApplicants: FailedApplicant[];
  isOpen: boolean;
  onClose: () => void;
  onRetryFailed: () => void;
  onClearFailed: () => void;
  isRetrying?: boolean;
}

export const FailedApplicantsModal: React.FC<FailedApplicantsModalProps> = ({
  failedApplicants,
  isOpen,
  onClose,
  onRetryFailed,
  onClearFailed,
  isRetrying = false,
}) => {
  if (!isOpen || failedApplicants.length === 0) return null;

  // Group failures by reason for better display
  const groupedFailures = failedApplicants.reduce(
    (groups, failure) => {
      const reason = failure.reason;
      if (!groups[reason]) {
        groups[reason] = [];
      }
      groups[reason].push(failure);
      return groups;
    },
    {} as Record<string, FailedApplicant[]>
  );

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <Dialog onClose={onClose} maxWidth="600px">
      <Dialog.CloseButton />
      <Heading variant="caps" marginBottom={3}>
        Failed Applicants ({failedApplicants.length})
      </Heading>

      <div className="max-h-96 overflow-y-auto mb-4">
        {Object.entries(groupedFailures).map(([reason, failures]) => (
          <div key={reason} className="mb-4 p-3 border rounded bg-red-50">
            <Text className="font-semibold text-red-800 mb-2">
              {reason} ({failures.length} applicants)
            </Text>

            <div className="space-y-2">
              {failures.map((failure, index) => (
                <div
                  key={failure.recordId}
                  className="p-2 bg-white rounded border-l-4 border-red-400"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <Text className="font-medium">
                        {failure.applicantName || `Applicant ${index + 1}`}
                      </Text>
                      <Text className="text-sm text-gray-600">
                        ID: {failure.recordId}
                      </Text>
                      <Text className="text-xs text-gray-500">
                        Batch {failure.batchNumber} •{' '}
                        {formatTimestamp(failure.timestamp)}
                      </Text>
                    </div>
                  </div>

                  {/* Show some applicant data if available */}
                  {failure.applicantData &&
                    Object.keys(failure.applicantData).length > 0 && (
                      <div className="mt-2 text-xs">
                        {Object.entries(failure.applicantData)
                          .slice(0, 2) // Show only first 2 fields to keep it compact
                          .map(
                            ([key, value]) =>
                              value?.trim() && (
                                <div key={key} className="text-gray-600">
                                  <span className="font-medium">{key}:</span>{' '}
                                  {value.length > 100
                                    ? `${value.substring(0, 97)}...`
                                    : value}
                                </div>
                              )
                          )}
                      </div>
                    )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 justify-end">
        <Button variant="secondary" onClick={onClearFailed} disabled={isRetrying}>
          Clear All Failed
        </Button>
        <Button
          variant="primary"
          onClick={onRetryFailed}
          disabled={isRetrying}
          icon={isRetrying ? 'time' : 'play'}
        >
          {isRetrying ? 'Retrying...' : 'Retry Failed Applicants'}
        </Button>
        <Button variant="default" onClick={onClose} disabled={isRetrying}>
          Close
        </Button>
      </div>
    </Dialog>
  );
};
