import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}) => {
  return (
    <div className="empty-container">
      <div className="empty-icon-wrapper">
        {icon || <Inbox size={40} className="empty-icon" />}
      </div>
      <h3 className="empty-title">{title}</h3>
      <p className="empty-description">{description}</p>
      {actionLabel && onAction && (
        <button className="btn btn-primary" onClick={onAction} style={{ marginTop: '1.25rem' }}>
          {actionLabel}
        </button>
      )}
    </div>
  );
};
