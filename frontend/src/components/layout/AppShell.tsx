import React, { useState } from 'react';
import { Sidebar, NavTab } from './Sidebar';
import { Header } from './Header';

interface AppShellProps {
  children: (activeTab: NavTab) => React.ReactNode;
}

const TAB_TITLES: Record<NavTab, { title: string; subtitle: string }> = {
  overview: {
    title: 'Platform Overview',
    subtitle: 'Autonomous AI Inference Optimization Platform for Arm64 Infrastructure',
  },
  models: {
    title: 'Model Registry',
    subtitle: 'Manage and register AI models optimized for Arm Neoverse runtimes',
  },
  experiments: {
    title: 'Optimization Experiments',
    subtitle: 'Search spaces, hardware targets, and latency budget constraints',
  },
  optimization: {
    title: 'Autonomous Tuning Engine',
    subtitle: 'Bayesian & TPE trial execution status across target infrastructure',
  },
  deployments: {
    title: 'Inference Deployments',
    subtitle: 'Active model serving endpoints and replica scaling',
  },
  system: {
    title: 'System Diagnostics',
    subtitle: 'Environment configuration, platform runtime, and database connection metrics',
  },
};

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');

  const { title, subtitle } = TAB_TITLES[activeTab];

  return (
    <div className="app-shell">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="main-viewport">
        <Header title={title} subtitle={subtitle} />
        <main className="content-area">{children(activeTab)}</main>
      </div>
    </div>
  );
};
