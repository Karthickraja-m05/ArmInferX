import React, { useEffect, useState } from 'react';
import {
  fetchSystemInfo,
  fetchReadiness,
  validateSystemConfig,
  SystemInfoResponse,
  ReadinessResponse,
  ConfigValidationResponse,
} from '../services/api';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { Server, Database, ShieldCheck, CheckCircle2, Code } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [sysInfo, setSysInfo] = useState<SystemInfoResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [validation, setValidation] = useState<ConfigValidationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [infoData, readyData, validData] = await Promise.all([
        fetchSystemInfo(),
        fetchReadiness(),
        validateSystemConfig(),
      ]);
      setSysInfo(infoData);
      setReadiness(readyData);
      setValidation(validData);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch system settings and diagnostics');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Validating System Configuration & Pydantic Schemas..." />;
  if (error) return <ErrorState title="Settings Error" message={error} onRetry={loadData} />;

  return (
    <div className="page-content">
      {/* Configuration Validation Status Banner */}
      <div className="panel-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldCheck size={20} style={{ color: 'var(--accent-emerald)' }} />
            <h3 className="panel-title">Production Configuration Schema Validation</h3>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Validated against Pydantic schema rules for AWS Graviton ARM64 deployment parameters.
          </p>
        </div>
        <span
          className="pill"
          style={{
            borderColor: validation?.valid ? 'var(--accent-emerald)' : 'var(--accent-rose)',
            color: validation?.valid ? 'var(--accent-emerald)' : 'var(--accent-rose)',
            fontSize: '0.9rem',
            padding: '6px 14px',
          }}
        >
          {validation?.valid ? 'SCHEMA VALID' : 'INVALID CONFIG'}
        </span>
      </div>

      {/* Real System Environment Parameters */}
      <div className="card-grid" style={{ marginTop: '1.5rem' }}>
        <div className="panel-card">
          <h3 className="panel-title">
            <Server size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-cyan)' }} />
            Platform Architecture & Runtime
          </h3>
          <ul className="info-list" style={{ marginTop: '0.75rem' }}>
            <li>
              <CheckCircle2 size={14} className="icon-success" />
              <strong>Application Name:</strong> {sysInfo?.app_name} ({sysInfo?.version})
            </li>
            <li>
              <CheckCircle2 size={14} className="icon-success" />
              <strong>Environment:</strong> {sysInfo?.environment}
            </li>
            <li>
              <CheckCircle2 size={14} className="icon-success" />
              <strong>Python Version:</strong> {sysInfo?.python_version}
            </li>
            <li>
              <CheckCircle2 size={14} className="icon-success" />
              <strong>Host Architecture:</strong> {sysInfo?.architecture} ({sysInfo?.platform})
            </li>
            <li>
              <CheckCircle2 size={14} className="icon-success" />
              <strong>Supported Runtimes:</strong> {sysInfo?.runtimes_supported.join(', ')}
            </li>
          </ul>
        </div>

        <div className="panel-card">
          <h3 className="panel-title">
            <Database size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-indigo)' }} />
            Database & Connection Pool Status
          </h3>
          <ul className="info-list" style={{ marginTop: '0.75rem' }}>
            <li>
              <CheckCircle2 size={14} className="icon-success" />
              <strong>Database Status:</strong> {readiness?.database}
            </li>
            <li>
              <CheckCircle2 size={14} className="icon-success" />
              <strong>Database Dialect:</strong> {sysInfo?.database_dialect}
            </li>
            <li>
              <CheckCircle2 size={14} className="icon-success" />
              <strong>Connection Latency:</strong> {readiness?.latency_ms} ms
            </li>
            <li>
              <CheckCircle2 size={14} className="icon-success" />
              <strong>Prometheus Observability:</strong> {sysInfo?.observability_enabled ? 'Enabled' : 'Disabled'}
            </li>
          </ul>
        </div>
      </div>

      {/* Validated Configuration JSON Summary */}
      <div className="panel-card" style={{ marginTop: '1.5rem' }}>
        <h3 className="panel-title">
          <Code size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-purple)' }} />
          Active Configuration Summary
        </h3>
        <pre
          style={{
            marginTop: '1rem',
            padding: '1rem',
            borderRadius: '6px',
            backgroundColor: '#0d1117',
            color: '#e6edf3',
            fontFamily: 'monospace',
            fontSize: '0.85rem',
            overflowX: 'auto',
          }}
        >
          {JSON.stringify(validation?.config_summary || {}, null, 2)}
        </pre>
      </div>
    </div>
  );
};
