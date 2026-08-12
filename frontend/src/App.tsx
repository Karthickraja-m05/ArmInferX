import { AppShell } from './components/layout/AppShell';
import { OverviewPage } from './pages/OverviewPage';
import { ModelsPage } from './pages/ModelsPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import { DeploymentsPage } from './pages/DeploymentsPage';
import { OptimizationPage } from './pages/OptimizationPage';
import { SystemPage } from './pages/SystemPage';
import './App.css';

export function App() {
  return (
    <AppShell>
      {(activeTab) => {
        switch (activeTab) {
          case 'overview':
            return <OverviewPage />;
          case 'models':
            return <ModelsPage />;
          case 'experiments':
            return <ExperimentsPage />;
          case 'deployments':
            return <DeploymentsPage />;
          case 'optimization':
            return <OptimizationPage />;
          case 'system':
            return <SystemPage />;
          default:
            return <OverviewPage />;
        }
      }}
    </AppShell>
  );
}

export default App;
