import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to load data',
  message,
  onRetry,
}) => {
  return (
    <div className="error-card">
      <div className="error-header">
        <AlertTriangle className="error-icon" size={24} />
        <div>
          <h3 className="error-title">{title}</h3>
          <p className="error-description">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button className="btn btn-secondary" onClick={onRetry} style={{ marginTop: '1rem' }}>
          <RefreshCw size={14} style={{ marginRight: '0.5rem' }} />
          Retry Connection
        </button>
      )}
    </div>
  );
};
