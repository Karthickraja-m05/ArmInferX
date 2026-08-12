import React, { useEffect, useState } from 'react';
import {
  fetchSystemInfo,
  fetchReadiness,
  fetchModels,
  fetchExperiments,
  SystemInfoResponse,
  ReadinessResponse,
} from '../services/api';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import {
  Server,
  Box,
  FlaskConical,
  Database,
  Cpu,
  ShieldCheck,
  CheckCircle,
} from 'lucide-react';

export const OverviewPage: React.FC = () => {
  const [sysInfo, setSysInfo] = useState<SystemInfoResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [modelCount, setModelCount] = useState<number>(0);
  const [expCount, setExpCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [infoData, readyData, modelsData, expsData] = await Promise.all([
        fetchSystemInfo(),
        fetchReadiness(),
        fetchModels(),
        fetchExperiments(),
      ]);
      setSysInfo(infoData);
      setReadiness(readyData);
      setModelCount(modelsData.length);
      setExpCount(expsData.length);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to connect to backend service.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Connecting to ArmServe Backend..." />;
  if (error) return <ErrorState title="Backend Connection Offline" message={error} onRetry={loadData} />;

  return (
    <div className="page-content">
      {/* Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Registered Models</span>
            <Box size={18} className="metric-icon" />
          </div>
          <div className="metric-value">{modelCount}</div>
          <div className="metric-footer">Real Database Records</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Active Experiments</span>
            <FlaskConical size={18} className="metric-icon" />
          </div>
          <div className="metric-value">{expCount}</div>
          <div className="metric-footer">Real Database Records</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Database Ping</span>
            <Database size={18} className="metric-icon" />
          </div>
          <div className="metric-value">
            {readiness?.latency_ms !== undefined ? `${readiness.latency_ms} ms` : 'N/A'}
          </div>
          <div className="metric-footer">
            Engine: {sysInfo?.database_dialect.toUpperCase()}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">System Health</span>
            <ShieldCheck size={18} className="metric-icon" />
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-emerald)' }}>
            {readiness?.status === 'ready' ? 'Ready' : 'Degraded'}
          </div>
          <div className="metric-footer">Env: {sysInfo?.environment}</div>
        </div>
      </div>

      {/* Real System Architecture Overview */}
      <div className="card-grid" style={{ marginTop: '1.5rem' }}>
        <div className="panel-card">
          <h3 className="panel-title">
            <Cpu size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-cyan)' }} />
            Arm64 Infrastructure Target Architecture
          </h3>
          <p className="panel-description">
            ArmServe compiles, quantizes, and optimizes AI models for execution on Arm Neoverse N1/N2/V1 cores (AWS Graviton, Azure Cobalt 100, GCP Axion).
          </p>
          <div className="tech-pills" style={{ marginTop: '1rem' }}>
            <span className="pill">ARM64 Neoverse</span>
            <span className="pill">ONNX Runtime</span>
            <span className="pill">SQLAlchemy 2.0 Async</span>
            <span className="pill">TimescaleDB / Postgres</span>
          </div>
        </div>

        <div className="panel-card">
          <h3 className="panel-title">
            <Server size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-emerald)' }} />
            Active Stack Verification
          </h3>
          <ul className="info-list" style={{ marginTop: '0.75rem' }}>
            <li>
              <CheckCircle size={14} className="icon-success" />
              <strong>Frontend SPA:</strong> React 18 + Vite (Port 5173 Proxy)
            </li>
            <li>
              <CheckCircle size={14} className="icon-success" />
              <strong>Backend REST API:</strong> FastAPI + Uvicorn (Port 8000)
            </li>
            <li>
              <CheckCircle size={14} className="icon-success" />
              <strong>Database Layer:</strong> {sysInfo?.database_dialect} connection pool
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
