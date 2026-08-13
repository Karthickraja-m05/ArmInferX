import React, { useEffect, useState } from 'react';
import {
  fetchSystemInfo,
  fetchReadiness,
  fetchActiveDeployment,
  fetchExperiments,
  fetchBenchmarkRuns,
  fetchOptimizationRecommendations,
  fetchAgentStatus,
  fetchDeploymentsHealth,
  SystemInfoResponse,
  ReadinessResponse,
  DeploymentRecord,
  AgentStatusResponse,
  RecommendationResponse,
} from '../services/api';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import {
  Server,
  Box,
  FlaskConical,
  Activity,
  ShieldCheck,

  CheckCircle,
  Rocket,
  Bot,
  Zap,
  TrendingUp,
} from 'lucide-react';

export const OverviewPage: React.FC = () => {
  const [sysInfo, setSysInfo] = useState<SystemInfoResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [activeDep, setActiveDep] = useState<DeploymentRecord | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatusResponse | null>(null);
  const [latestRec, setLatestRec] = useState<RecommendationResponse | null>(null);
  const [expCount, setExpCount] = useState<number>(0);
  const [benchCount, setBenchCount] = useState<number>(0);
  const [optCount, setOptCount] = useState<number>(0);
  const [healthStatus, setHealthStatus] = useState<string>('HEALTHY');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        infoData,
        readyData,
        activeDepData,
        expsData,
        benchData,
        recsData,
        agentData,
        healthData,
      ] = await Promise.allSettled([
        fetchSystemInfo(),
        fetchReadiness(),
        fetchActiveDeployment(),
        fetchExperiments(),
        fetchBenchmarkRuns(),
        fetchOptimizationRecommendations(),
        fetchAgentStatus(),
        fetchDeploymentsHealth(),
      ]);

      if (infoData.status === 'fulfilled') setSysInfo(infoData.value);
      if (readyData.status === 'fulfilled') setReadiness(readyData.value);
      if (activeDepData.status === 'fulfilled') setActiveDep(activeDepData.value);
      if (expsData.status === 'fulfilled') setExpCount(expsData.value.length);
      if (benchData.status === 'fulfilled') setBenchCount(benchData.value.runs?.length || 0);
      if (recsData.status === 'fulfilled') {
        const recs = recsData.value.recommendations || [];
        setOptCount(recs.length);
        if (recs.length > 0) setLatestRec(recs[0]);
      }
      if (agentData.status === 'fulfilled') setAgentStatus(agentData.value);
      if (healthData.status === 'fulfilled') setHealthStatus(healthData.value.status.toUpperCase());
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
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <LoadingState message="Connecting to ArmServe Backend Core..." />;
  if (error) return <ErrorState title="Backend Connection Error" message={error} onRetry={loadData} />;

  return (
    <div className="page-content">
      {/* Platform Real-Time Metrics Grid */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Active Deployment</span>
            <Rocket size={18} className="metric-icon" style={{ color: 'var(--accent-cyan)' }} />
          </div>
          <div className="metric-value">{activeDep?.name || 'prod-release-v1'}</div>
          <div className="metric-footer">Version: {activeDep?.deployment_version || 'v1.0.1'}</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Current Model</span>
            <Box size={18} className="metric-icon" style={{ color: 'var(--accent-indigo)' }} />
          </div>
          <div className="metric-value">{activeDep?.model_version_id || 'qwen2.5-0.5b-instruct'}</div>
          <div className="metric-footer">Runtime: {activeDep?.runtime_version || '1.0.0-arm64'}</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">System Health</span>
            <ShieldCheck size={18} className="metric-icon" style={{ color: 'var(--accent-emerald)' }} />
          </div>
          <div className="metric-value" style={{ color: healthStatus === 'HEALTHY' ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
            {healthStatus}
          </div>
          <div className="metric-footer">Readiness: {readiness?.status === 'ready' ? 'Ready (200 OK)' : 'Degraded'}</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Optimization Agent</span>
            <Bot size={18} className="metric-icon" style={{ color: 'var(--accent-purple)' }} />
          </div>
          <div className="metric-value" style={{ color: agentStatus?.is_running ? 'var(--accent-emerald)' : 'var(--accent-cyan)' }}>
            {agentStatus?.state || 'IDLE'}
          </div>
          <div className="metric-footer">Goal: {agentStatus?.goal || 'AWS Graviton3 Latency Reduction'}</div>
        </div>
      </div>

      {/* Real Statistics Row */}
      <div className="card-grid" style={{ marginTop: '1.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <div className="panel-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FlaskConical size={18} style={{ color: 'var(--accent-cyan)' }} />
            <span className="panel-title" style={{ fontSize: '0.9rem' }}>Total Experiments</span>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '0.5rem', color: 'var(--text-main)' }}>
            {expCount}
          </div>
        </div>

        <div className="panel-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={18} style={{ color: 'var(--accent-emerald)' }} />
            <span className="panel-title" style={{ fontSize: '0.9rem' }}>Total Benchmarks</span>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '0.5rem', color: 'var(--text-main)' }}>
            {benchCount}
          </div>
        </div>

        <div className="panel-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Zap size={18} style={{ color: 'var(--accent-amber)' }} />
            <span className="panel-title" style={{ fontSize: '0.9rem' }}>Completed Optimizations</span>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '0.5rem', color: 'var(--text-main)' }}>
            {optCount}
          </div>
        </div>
      </div>

      {/* Latest Recommendation & Stack Overview */}
      <div className="card-grid" style={{ marginTop: '1.5rem' }}>
        <div className="panel-card">
          <h3 className="panel-title">
            <TrendingUp size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-amber)' }} />
            Latest Optimization Recommendation
          </h3>
          {latestRec ? (
            <div style={{ marginTop: '1rem' }}>
              <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                Config: {latestRec.best_config_id} (Threads: {latestRec.optimal_thread_count}, Batch: {latestRec.optimal_batch_size})
              </div>
              <p style={{ marginTop: '0.5rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                {latestRec.explanation}
              </p>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', fontSize: '0.85rem' }}>
                <span className="pill">Est P50: {latestRec.expected_p50_latency_ms} ms</span>
                <span className="pill">Est TPS: {latestRec.expected_throughput_tps} tok/s</span>
                <span className="pill" style={{ borderColor: 'var(--accent-emerald)', color: 'var(--accent-emerald)' }}>
                  Gain: +{latestRec.performance_gain_pct}%
                </span>
              </div>
            </div>
          ) : (
            <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>
              No optimization recommendations generated yet. Run the Autonomous Optimization Agent to generate recommendations.
            </p>
          )}
        </div>

        <div className="panel-card">
          <h3 className="panel-title">
            <Server size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-emerald)' }} />
            Target Infrastructure & Environment
          </h3>
          <ul className="info-list" style={{ marginTop: '0.75rem' }}>
            <li>
              <CheckCircle size={14} className="icon-success" />
              <strong>Architecture:</strong> {sysInfo?.architecture || 'aarch64'} (AWS Graviton3 / Neoverse V1)
            </li>
            <li>
              <CheckCircle size={14} className="icon-success" />
              <strong>Python Environment:</strong> {sysInfo?.python_version} ({sysInfo?.environment})
            </li>
            <li>
              <CheckCircle size={14} className="icon-success" />
              <strong>Database dialect:</strong> {sysInfo?.database_dialect}
            </li>
            <li>
              <CheckCircle size={14} className="icon-success" />
              <strong>Supported Runtimes:</strong> {sysInfo?.runtimes_supported?.join(', ') || 'ONNXRuntime, GGUF-MLAS'}
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
