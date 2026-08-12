import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ message = 'Loading system data...' }) => {
  return (
    <div className="loading-container">
      <Loader2 className="spinner-icon" size={32} />
      <p className="loading-message">{message}</p>
    </div>
  );
};
