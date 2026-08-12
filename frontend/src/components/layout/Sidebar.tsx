import React from 'react';
import {
  LayoutDashboard,
  FlaskConical,
  Box,
  Rocket,
  Cpu,
  Server,
  Activity,
} from 'lucide-react';

export type NavTab = 'overview' | 'experiments' | 'models' | 'deployments' | 'optimization' | 'system';

interface SidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const navItems: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={18} /> },
    { id: 'models', label: 'Models', icon: <Box size={18} /> },
    { id: 'experiments', label: 'Experiments', icon: <FlaskConical size={18} /> },
    { id: 'optimization', label: 'Optimization', icon: <Cpu size={18} /> },
    { id: 'deployments', label: 'Deployments', icon: <Rocket size={18} /> },
    { id: 'system', label: 'System', icon: <Server size={18} /> },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo-icon">
          <Activity size={20} className="brand-activity" />
        </div>
        <div className="brand-text">
          <span className="brand-name">ArmServe</span>
          <span className="brand-tag">Arm64 AI Engine</span>
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
          <span>Target: Arm64 Neoverse</span>
        </div>
      </div>
    </aside>
  );
};
