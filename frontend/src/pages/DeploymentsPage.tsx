import React from 'react';
import { EmptyState } from '../components/common/EmptyState';
import { Rocket, Info } from 'lucide-react';

export const DeploymentsPage: React.FC = () => {
  return (
    <div className="page-content">
      <div className="status-notice-card">
        <Info size={20} className="notice-icon" />
        <div>
          <h4 className="notice-title">Inference Deployment Engine</h4>
          <p className="notice-description">
            The database deployment model schema (`deployments` and `deployment_events`) is initialized. Active infrastructure worker deployments on K8s / Graviton instances will be orchestrated in subsequent sprints.
          </p>
        </div>
      </div>

      <div style={{ marginTop: '2rem' }}>
        <EmptyState
          icon={<Rocket size={44} />}
          title="No Active Deployments"
          description="There are currently no active model serving endpoints deployed in database records."
        />
      </div>
    </div>
  );
};
