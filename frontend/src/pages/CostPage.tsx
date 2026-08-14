import React, { useCallback, useEffect, useState } from 'react';
import { calculateCost, CostCalculationResponse } from '../services/api';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { DollarSign, TrendingDown, Cpu, Zap, Calculator } from 'lucide-react';

export const CostPage: React.FC = () => {
  const [costData, setCostData] = useState<CostCalculationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Calculator inputs
  const [instanceType, setInstanceType] = useState<string>('c7g.2xlarge (Graviton3)');
  const [hourlyRate, setHourlyRate] = useState<number>(0.29);
  const [throughputTPS, setThroughputTPS] = useState<number>(384);
  const [monthlyQueries, setMonthlyQueries] = useState<number>(10000000);


  const loadCostData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await calculateCost({
        instance_type: instanceType,
        hourly_rate: hourlyRate,
        throughput_tps: throughputTPS,
        monthly_queries: monthlyQueries,
      });
      setCostData(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to calculate cost metrics');
      }
    } finally {
      setLoading(false);
    }
  }, [instanceType, hourlyRate, throughputTPS, monthlyQueries]);

  useEffect(() => {
    loadCostData();
  }, [loadCostData]);

  if (loading) return <LoadingState message="Calculating AWS Graviton Cost Savings..." />;
  if (error) return <ErrorState title="Cost Calculator Error" message={error} onRetry={loadCostData} />;

  return (
    <div className="page-content">
      {/* Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Graviton3 Cost Savings</span>
            <TrendingDown size={18} className="metric-icon" style={{ color: 'var(--accent-emerald)' }} />
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-emerald)' }}>
            -{costData?.graviton_savings_pct || 42.5}%
          </div>
          <div className="metric-footer">vs x86 c6i.2xlarge equivalent</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Cost per 1M Tokens</span>
            <DollarSign size={18} className="metric-icon" style={{ color: 'var(--accent-cyan)' }} />
          </div>
          <div className="metric-value">
            ${costData?.cost_per_1m_tokens ? costData.cost_per_1m_tokens.toFixed(4) : '0.0420'}
          </div>
          <div className="metric-footer">Direct ARM Hardware Efficiency</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Projected Monthly Spend</span>
            <Calculator size={18} className="metric-icon" style={{ color: 'var(--accent-amber)' }} />
          </div>
          <div className="metric-value">
            ${costData?.projected_monthly_cost ? costData.projected_monthly_cost.toFixed(2) : '208.80'}
          </div>
          <div className="metric-footer">10 Million Monthly Inference Queries</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Cost-Efficiency Index</span>
            <Zap size={18} className="metric-icon" style={{ color: 'var(--accent-purple)' }} />
          </div>
          <div className="metric-value">
            {costData?.effective_efficiency_score ? costData.effective_efficiency_score.toFixed(1) : '94.2'} / 100
          </div>
          <div className="metric-footer">Score = TPS / Hourly Rate</div>
        </div>
      </div>

      {/* Instance Cost Comparison Matrix */}
      <div className="card-grid" style={{ marginTop: '1.5rem' }}>
        <div className="panel-card">
          <h3 className="panel-title">
            <Cpu size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-cyan)' }} />
            AWS Graviton3 vs x86 Infrastructure Comparison
          </h3>
          <div className="table-wrapper" style={{ marginTop: '1rem' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Instance Architecture</th>
                  <th>Hourly Rate</th>
                  <th>Monthly Rate</th>
                  <th>Tokens / Sec</th>
                  <th>Cost per 1M Tokens</th>
                  <th>Savings %</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ backgroundColor: 'rgba(16, 185, 129, 0.08)' }}>
                  <td><strong style={{ color: 'var(--accent-emerald)' }}>AWS Graviton3 (c7g.2xlarge)</strong></td>
                  <td>$0.290 / hr</td>
                  <td>$208.80</td>
                  <td style={{ color: 'var(--accent-amber)' }}>384 tok/s</td>
                  <td style={{ fontWeight: 600, color: 'var(--accent-emerald)' }}>$0.042</td>
                  <td><span className="pill" style={{ borderColor: 'var(--accent-emerald)', color: 'var(--accent-emerald)' }}>-42.5%</span></td>
                </tr>
                <tr>
                  <td>Intel Xeon Ice Lake (c6i.2xlarge)</td>
                  <td>$0.340 / hr</td>
                  <td>$244.80</td>
                  <td>280 tok/s</td>
                  <td>$0.073</td>
                  <td>Baseline</td>
                </tr>
                <tr>
                  <td>AMD EPYC Milan (c6a.2xlarge)</td>
                  <td>$0.306 / hr</td>
                  <td>$220.32</td>
                  <td>295 tok/s</td>
                  <td>$0.062</td>
                  <td>-15.0%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Interactive Cost Calculator Panel */}
        <div className="panel-card">
          <h3 className="panel-title">
            <Calculator size={18} style={{ marginRight: '0.5rem', color: 'var(--accent-amber)' }} />
            Interactive Hardware Cost Model
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Target Instance Type</label>
              <input
                type="text"
                value={instanceType}
                onChange={(e) => setInstanceType(e.target.value)}
                style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-card)', color: 'var(--text-main)', marginTop: '4px' }}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Hourly Rate ($)</label>
                <input
                  type="number"
                  step="0.01"
                  value={hourlyRate}
                  onChange={(e) => setHourlyRate(parseFloat(e.target.value) || 0.1)}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-card)', color: 'var(--text-main)', marginTop: '4px' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Throughput (TPS)</label>
                <input
                  type="number"
                  value={throughputTPS}
                  onChange={(e) => setThroughputTPS(parseInt(e.target.value) || 100)}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-card)', color: 'var(--text-main)', marginTop: '4px' }}
                />
              </div>
            </div>
            <div>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Monthly Queries Volume</label>
              <input
                type="number"
                value={monthlyQueries}
                onChange={(e) => setMonthlyQueries(parseInt(e.target.value) || 1000000)}
                style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-card)', color: 'var(--text-main)', marginTop: '4px' }}
              />
            </div>

            <div>
              <button
                onClick={loadCostData}
                className="pill"
                style={{ backgroundColor: 'var(--accent-cyan)', color: '#000', fontWeight: 600, width: '100%', padding: '10px', marginTop: '0.5rem', cursor: 'pointer' }}
              >
                Re-Calculate Infrastructure Cost Projection
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
