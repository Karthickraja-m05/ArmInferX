import React, { useEffect, useState } from 'react';
import {
  fetchSystemInfo,
  fetchReadiness,
  SystemInfoResponse,
  ReadinessResponse,
} from '../services/api';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { Server, Database, ShieldCheck, Terminal, HardDrive } from 'lucide-react';

export const SystemPage: React.FC = () => {
  const [sysInfo, setSysInfo] = useState<SystemInfoResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [info, ready] = await Promise.all([
        fetchSystemInfo(),
        fetchReadiness(),
      ]);
      setSysInfo(info);
      setReadiness(ready);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch system info from backend');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Fetching Real System Diagnostics from Backend..." />;
  if (error) return <ErrorState title="System Diagnostics Offline" message={error} onRetry={loadData} />;

  return (
    <div className="page-content">
      <div className="panel-card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 className="panel-title" style={{ fontSize: '1.25rem' }}>
              <Server size={20} style={{ marginRight: '0.5rem', color: 'var(--accent-cyan)' }} />
              Real Backend System Diagnostics
            </h2>
            <p className="panel-description">
              Retrieved directly from REST API endpoint: <code className="code-text">/api/v1/system/info</code>
            </p>
          </div>
          <span className="badge badge-emerald" style={{ padding: '0.4rem 0.8rem', fontSize: '0.875rem' }}>
            <ShieldCheck size={14} style={{ marginRight: '0.4rem' }} />
            Secrets Masked & Secure
          </span>
        </div>
      </div>

      <div className="card-grid">
        {/* Environment & App Card */}
        <div className="panel-card">
          <h3 className="panel-title">
            <Terminal size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-purple)' }} />
            Application & Runtime
          </h3>
          <table className="info-table" style={{ marginTop: '1rem' }}>
            <tbody>
              <tr>
                <td>Application Title:</td>
                <td className="font-semibold">{sysInfo?.app_name}</td>
              </tr>
              <tr>
                <td>App Version:</td>
                <td>
                  <span className="badge badge-blue">v{sysInfo?.version}</span>
                </td>
              </tr>
              <tr>
                <td>API Version:</td>
                <td>{sysInfo?.api_version}</td>
              </tr>
              <tr>
                <td>Environment:</td>
                <td>
                  <span className="badge badge-emerald">{sysInfo?.environment}</span>
                </td>
              </tr>
              <tr>
                <td>Python Version:</td>
                <td className="code-text">{sysInfo?.python_version}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Host Platform Card */}
        <div className="panel-card">
          <h3 className="panel-title">
            <HardDrive size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-cyan)' }} />
            Host OS & Architecture
          </h3>
          <table className="info-table" style={{ marginTop: '1rem' }}>
            <tbody>
              <tr>
                <td>Operating System:</td>
                <td className="font-semibold">{sysInfo?.platform}</td>
              </tr>
              <tr>
                <td>CPU Architecture:</td>
                <td className="font-semibold">{sysInfo?.architecture}</td>
              </tr>
              <tr>
                <td>Supported Runtimes:</td>
                <td>
                  {sysInfo?.runtimes_supported.map((r) => (
                    <span key={r} className="badge badge-purple" style={{ marginRight: '0.25rem' }}>
                      {r}
                    </span>
                  ))}
                </td>
              </tr>
              <tr>
                <td>Observability:</td>
                <td>{sysInfo?.observability_enabled ? 'Prometheus Enabled' : 'Disabled'}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Database Connection Status Card */}
      <div className="panel-card" style={{ marginTop: '1.5rem' }}>
        <h3 className="panel-title">
          <Database size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-emerald)' }} />
          Database Connection & Pool Status
        </h3>

        <div className="metrics-grid" style={{ marginTop: '1rem' }}>
          <div className="metric-card" style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
            <span className="metric-label">Engine Dialect</span>
            <div className="metric-value" style={{ fontSize: '1.5rem', textTransform: 'uppercase' }}>
              {sysInfo?.database_dialect}
            </div>
          </div>

          <div className="metric-card" style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
            <span className="metric-label">Readiness State</span>
            <div
              className="metric-value"
              style={{
                fontSize: '1.5rem',
                color: readiness?.status === 'ready' ? 'var(--accent-emerald)' : '#ef4444',
              }}
            >
              {readiness?.status}
            </div>
          </div>

          <div className="metric-card" style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
            <span className="metric-label">Query Ping Latency</span>
            <div className="metric-value" style={{ fontSize: '1.5rem' }}>
              {readiness?.latency_ms !== undefined ? `${readiness.latency_ms} ms` : 'N/A'}
            </div>
          </div>
        </div>

        {readiness?.pool_info && Object.keys(readiness.pool_info).length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem' }}>
              Engine Connection Pool Metrics
            </h4>
            <div className="tech-pills">
              <span className="pill">Size: {readiness.pool_info.size}</span>
              <span className="pill">Checked In: {readiness.pool_info.checked_in}</span>
              <span className="pill">Checked Out: {readiness.pool_info.checked_out}</span>
              <span className="pill">Overflow: {readiness.pool_info.overflow}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
