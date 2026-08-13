import React from 'react';
import {
  LayoutDashboard,
  FlaskConical,
  Rocket,
  Cpu,
  Server,
  Activity,
  Award,
  DollarSign,
  Bot,
} from 'lucide-react';

export type NavTab =
  | 'overview'
  | 'benchmarks'
  | 'experiments'
  | 'optimization'
  | 'quality'
  | 'cost'
  | 'deployments'
  | 'agent'
  | 'performix'
  | 'settings';

interface SidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const navItems: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Home Overview', icon: <LayoutDashboard size={18} /> },
    { id: 'benchmarks', label: 'Benchmarks', icon: <Activity size={18} /> },
    { id: 'experiments', label: 'Experiments', icon: <FlaskConical size={18} /> },
    { id: 'optimization', label: 'Optimization', icon: <Cpu size={18} /> },
    { id: 'quality', label: 'Quality', icon: <Award size={18} /> },
    { id: 'cost', label: 'Cost Analytics', icon: <DollarSign size={18} /> },
    { id: 'deployments', label: 'Deployments', icon: <Rocket size={18} /> },
    { id: 'agent', label: 'Agent Activity', icon: <Bot size={18} /> },
    { id: 'performix', label: 'Arm Performix', icon: <Award size={18} /> },
    { id: 'settings', label: 'Settings', icon: <Server size={18} /> },
  ];


  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo-icon">
          <Activity size={20} className="brand-activity" />
        </div>
        <div className="brand-text">
          <span className="brand-name">ArmServe</span>
          <span className="brand-tag">AWS Graviton3 Engine</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => onTabChange(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="arch-badge">
          <span className="arch-dot"></span>
          <span>AWS ARM64 Graviton3</span>
        </div>
      </div>
    </aside>
  );
};
