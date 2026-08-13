import React, { useEffect, useState } from 'react';
import { fetchReadiness, ReadinessResponse } from '../../services/api';
import { CheckCircle2, XCircle, RefreshCw, Database } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadStatus = async () => {
    setIsRefreshing(true);
    try {
      const data = await fetchReadiness();
      setReadiness(data);
    } catch {
      setReadiness({
        status: 'not_ready',
        database: 'disconnected',
        timestamp: new Date().toISOString(),
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const isReady = readiness?.status === 'ready' || readiness?.database === 'connected';

  return (
    <header className="app-header">
      <div className="header-titles">
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>

      <div className="header-status-group">
        {readiness && (
          <div className="db-ping-tag">
            <Database size={14} style={{ marginRight: '0.4rem' }} />
            <span>DB: {readiness.database}</span>
            {readiness.latency_ms !== undefined && readiness.latency_ms !== null && (
              <span className="latency-val">({readiness.latency_ms}ms)</span>
            )}
          </div>
        )}

        <div className={`status-badge ${isReady ? 'ready' : 'not-ready'}`}>
          {isReady ? (
            <>
              <CheckCircle2 size={14} style={{ marginRight: '0.4rem' }} />
              <span>Backend Connected</span>
            </>
          ) : (
            <>
              <XCircle size={14} style={{ marginRight: '0.4rem' }} />
              <span>Backend Offline</span>
            </>
          )}
        </div>

        <button
          className={`btn-icon ${isRefreshing ? 'spinning' : ''}`}
          onClick={loadStatus}
          title="Refresh Status"
        >
          <RefreshCw size={16} />
        </button>
      </div>
    </header>
  );
};
