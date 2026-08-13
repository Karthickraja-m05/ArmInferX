import { AppShell } from './components/layout/AppShell';
import { OverviewPage } from './pages/OverviewPage';
import { BenchmarksPage } from './pages/BenchmarksPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import { OptimizationPage } from './pages/OptimizationPage';
import { QualityPage } from './pages/QualityPage';
import { CostPage } from './pages/CostPage';
import { DeploymentsPage } from './pages/DeploymentsPage';
import { AgentPage } from './pages/AgentPage';
import { PerformixPage } from './pages/PerformixPage';
import { SettingsPage } from './pages/SettingsPage';
import './App.css';

export function App() {
  return (
    <AppShell>
      {(activeTab) => {
        switch (activeTab) {
          case 'overview':
            return <OverviewPage />;
          case 'benchmarks':
            return <BenchmarksPage />;
          case 'experiments':
            return <ExperimentsPage />;
          case 'optimization':
            return <OptimizationPage />;
          case 'quality':
            return <QualityPage />;
          case 'cost':
            return <CostPage />;
          case 'deployments':
            return <DeploymentsPage />;
          case 'agent':
            return <AgentPage />;
          case 'performix':
            return <PerformixPage />;
          case 'settings':
            return <SettingsPage />;
          default:
            return <OverviewPage />;
        }
      }}
    </AppShell>
  );
}


export default App;
