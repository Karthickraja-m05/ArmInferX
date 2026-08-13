import React, { useState } from 'react';
import { Sidebar, NavTab } from './Sidebar';
import { Header } from './Header';

interface AppShellProps {
  children: (activeTab: NavTab) => React.ReactNode;
}

const TAB_TITLES: Record<NavTab, { title: string; subtitle: string }> = {
  overview: {
    title: 'Platform System Overview',
    subtitle: 'Autonomous AI Inference Optimization Platform for AWS ARM64 Graviton Infrastructure',
  },
  benchmarks: {
    title: 'Benchmark & Experiment Telemetry',
    subtitle: 'Latency trends, TTFT, throughput, CPU & RAM footprint telemetry',
  },
  experiments: {
    title: 'Optimization Experiments',
    subtitle: 'Search spaces, hardware targets, trial execution, and budget constraints',
  },
  optimization: {
    title: 'Optimization Analytics & Pareto Frontier',
    subtitle: 'Multi-objective ranking, performance gain, and constraint rejection rationale',
  },
  quality: {
    title: 'Quality Evaluation & Semantic Scoring',
    subtitle: 'BLEU, ROUGE-L, and cosine semantic similarity non-degradation verification',
  },
  cost: {
    title: 'AWS Graviton3 Cost Analytics',
    subtitle: 'Cost per 1M tokens, monthly spend projections, and x86 hardware comparison',
  },
  deployments: {
    title: 'Inference Deployment Monitoring',
    subtitle: '5-stage health verification, active deployments, and automated zero-downtime rollback',
  },
  agent: {
    title: 'Autonomous Optimization Agent Activity',
    subtitle: 'Live workflow states, observation cycles, optimization plans, and decision audit logs',
  },
  performix: {
    title: 'Arm Performix Official Integration & Evidence',
    subtitle: 'Official Arm benchmark suite correlation, hardware metrics, and hackathon submission evidence',
  },
  settings: {
    title: 'System Settings & Diagnostics',
    subtitle: 'Pydantic configuration schema validation, environment variables, and connection pool metrics',
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
