import React from 'react';
import { EmptyState } from '../components/common/EmptyState';
import { Cpu, Info } from 'lucide-react';

export const OptimizationPage: React.FC = () => {
  return (
    <div className="page-content">
      <div className="status-notice-card">
        <Info size={20} className="notice-icon" />
        <div>
          <h4 className="notice-title">Autonomous Optimization Controller</h4>
          <p className="notice-description">
            The database schema (`optimization_runs`, `trials`) is fully migrated. Optuna TPE optimization workers will execute automated trial trials in future sprints.
          </p>
        </div>
      </div>

      <div style={{ marginTop: '2rem' }}>
        <EmptyState
          icon={<Cpu size={44} />}
          title="No Active Optimization Runs"
          description="No autonomous hyperparameter search trials are currently running."
        />
      </div>
    </div>
  );
};
