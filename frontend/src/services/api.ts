import { ENV } from '../config/env';

// ---------------------------------------------------------------------------
// Common & System API Types
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  environment: string;
  database: string;
  timestamp?: string;
}

export interface PoolInfo {
  size?: number;
  checked_in?: number;
  checked_out?: number;
  overflow?: number;
}

export interface ReadinessResponse {
  status: string;
  database: string;
  latency_ms?: number;
  timestamp?: string;
  pool_info?: PoolInfo;
}

export interface SystemInfoResponse {
  app_name: string;
  version: string;
  environment: string;
  api_version: string;
  python_version: string;
  platform: string;
  architecture: string;
  database_dialect: string;
  runtimes_supported: string[];
  observability_enabled: boolean;
}

export interface ConfigValidationResponse {
  valid: boolean;
  environment: string;
  errors: string[];
  config_summary: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Model API Types
// ---------------------------------------------------------------------------

export interface ModelRegister {
  name: string;
  source: string;
  format: string;
  quantization: string;
}

export interface ModelResponse {
  id: string;
  name: string;
  source: string;
  format: string;
  quantization: string;
  size_bytes: number;
  storage_uri: string;
  compatible_runtimes: string[];
  metadata_info: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Benchmark & Experiment API Types
// ---------------------------------------------------------------------------

export interface BenchmarkRunPayload {
  model_id: string;
  thread_count: number;
  batch_size: number;
  context_length: number;
  iterations: number;
  concurrency: number;
}

export interface BenchmarkRunResponse {
  run_id: string;
  model_id: string;
  latency_p50_ms: number;
  latency_p90_ms: number;
  latency_p99_ms: number;
  throughput_rps: number;
  tokens_per_second: number;
  ttft_ms: number;
  cpu_percent: number;
  memory_used_mb: number;
  status: string;
  created_at: string;
}

export interface PerformanceConstraints {
  max_latency_p99_ms?: number;
  min_throughput_rps?: number;
}

export interface SearchSpace {
  runtimes?: string[];
  quantizations?: string[];
  instance_types?: string[];
  batch_sizes?: number[];
}

export interface ExperimentCreate {
  name: string;
  model_id: string;
  constraints: PerformanceConstraints;
  search_space: SearchSpace;
  budget: number;
}

export interface ExperimentResponse {
  id: string;
  name: string;
  status: string;
  model_id: string;
  constraints: Record<string, unknown>;
  search_space: Record<string, unknown>;
  budget: number;
  created_at: string;
  updated_at: string;
  trials: unknown[];
}

// ---------------------------------------------------------------------------
// Optimization API Types
// ---------------------------------------------------------------------------

export interface RankedConfigItem {
  rank: number;
  config_id: string;
  thread_count: number;
  batch_size: number;
  latency_p50_ms: number;
  throughput_tps: number;
  score: number;
  quality_score?: number;
  cost_per_1m_tokens?: number;
  status?: string;
  rejection_reason?: string;
}

export interface OptimizationRankingsResponse {
  model_id: string;
  total_configs_evaluated: number;
  top_configurations: RankedConfigItem[];
  rejected_configurations: RankedConfigItem[];
}

export interface RecommendationResponse {
  recommendation_id: string;
  model_id: string;
  best_config_id: string;
  optimal_thread_count: number;
  optimal_batch_size: number;
  score: number;
  explanation: string;
  expected_p50_latency_ms: number;
  expected_throughput_tps: number;
  performance_gain_pct: number;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Quality API Types
// ---------------------------------------------------------------------------

export interface QualityDatasetItem {
  dataset_id: string;
  name: string;
  sample_count: number;
  domain: string;
  created_at: string;
}

export interface QualityEvaluationResult {
  eval_id: string;
  model_id: string;
  bleu_score: number;
  rouge_score: number;
  semantic_similarity: number;
  overall_score: number;
  passed: boolean;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Cost API Types
// ---------------------------------------------------------------------------

export interface CostCalculationRequest {
  instance_type: string;
  hourly_rate: number;
  throughput_tps: number;
  monthly_queries: number;
}

export interface CostCalculationResponse {
  calc_id: string;
  instance_type: string;
  cost_per_1m_tokens: number;
  projected_monthly_cost: number;
  graviton_savings_pct: number;
  effective_efficiency_score: number;
}

// ---------------------------------------------------------------------------
// Deployment API Types
// ---------------------------------------------------------------------------

export interface DeploymentRecord {
  id: string;
  name: string;
  model_version_id: string;
  environment: string;
  status: string;
  endpoint_url?: string;
  replicas: number;
  configuration: Record<string, unknown>;
  deployment_version: string;
  runtime_version: string;
  config_version: string;
  is_active: boolean;
  health_status: string;
  metrics_summary: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DeploymentCreateRequest {
  name: string;
  model_version_id: string;
  configuration: Record<string, unknown>;
  environment?: string;
  replicas?: number;
  runtime_version?: string;
}

export interface DeploymentHealthSummary {
  status: string;
  active_deployment_id?: string;
  health_history: Array<Record<string, unknown>>;
}

export interface DeploymentTelemetry {
  deployment_id: string;
  request_count: number;
  requests_per_second: number;
  tokens_per_second: number;
  latency_p50_ms: number;
  latency_p90_ms: number;
  latency_p99_ms: number;
  cpu_utilization_percent: number;
  memory_used_mb: number;
  error_rate_percent: number;
  availability_percent: number;
  active_alerts: Array<Record<string, unknown>>;
}

export interface RollbackResponse {
  success: boolean;
  restored_deployment_id: string;
  rolled_back_deployment_id: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Autonomous Agent API Types
// ---------------------------------------------------------------------------

export interface AgentStatusResponse {
  is_running: boolean;
  current_workflow_id?: string;
  state: string;
  current_step: number;
  total_steps: number;
  goal: string;
  active_plan?: string;
  latest_observation?: string;
  stopping_reason?: string;
}

export interface AgentDecisionRecord {
  decision_id: string;
  step_index: number;
  action_type: string;
  rationale: string;
  confidence_score: number;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// HTTP Request Helper
// ---------------------------------------------------------------------------

export interface ApiError {
  error_code?: string;
  message: string;
  details?: unknown;
}

export function buildUrl(endpoint: string): string {
  const base = (ENV.API_BASE_URL || '').trim().replace(/\/+$/, '');
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return base ? `${base}${cleanEndpoint}` : cleanEndpoint;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = buildUrl(endpoint);
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      if (response.status === 502 || response.status === 503 || response.status === 504) {
        throw new Error(
          `Backend server is starting up or temporarily unavailable (HTTP ${response.status}). If hosted on Render Free tier, please wait 30-60 seconds for it to wake up.`
        );
      }

      let errorData: ApiError | null = null;
      try {
        errorData = await response.json();
      } catch {
        // Non-JSON response
      }
      const errorMessage = errorData?.message || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (err: unknown) {
    if (err instanceof Error) {
      throw err;
    }
    throw new Error('An unknown network error occurred while contacting the backend.');
  }
}

// ---------------------------------------------------------------------------
// API Client Functions
// ---------------------------------------------------------------------------

// System & Health APIs
export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

export async function fetchReadiness(): Promise<ReadinessResponse> {
  return request<ReadinessResponse>('/ready');
}

export async function fetchSystemInfo(): Promise<SystemInfoResponse> {
  return request<SystemInfoResponse>('/api/v1/system/info');
}

export async function validateSystemConfig(): Promise<ConfigValidationResponse> {
  return request<ConfigValidationResponse>('/api/v1/system/config/validate');
}

// Model Registry APIs
export async function fetchModels(): Promise<ModelResponse[]> {
  return request<ModelResponse[]>('/api/v1/models');
}

export async function registerModel(payload: ModelRegister): Promise<ModelResponse> {
  return request<ModelResponse>('/api/v1/models', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// Benchmark & Experiment APIs
export async function fetchBenchmarkRuns(): Promise<{ runs: BenchmarkRunResponse[] }> {
  return request<{ runs: BenchmarkRunResponse[] }>('/api/v1/benchmarks/runs');
}

export async function runBenchmark(payload: BenchmarkRunPayload): Promise<BenchmarkRunResponse> {
  return request<BenchmarkRunResponse>('/api/v1/benchmarks/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchExperiments(): Promise<ExperimentResponse[]> {
  return request<ExperimentResponse[]>('/api/v1/experiments');
}

export async function createExperiment(payload: ExperimentCreate): Promise<ExperimentResponse> {
  return request<ExperimentResponse>('/api/v1/experiments', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// Optimization APIs
export async function fetchOptimizationRankings(): Promise<OptimizationRankingsResponse> {
  return request<OptimizationRankingsResponse>('/api/v1/optimization/rankings');
}

export async function fetchOptimizationRecommendations(): Promise<{ recommendations: RecommendationResponse[] }> {
  return request<{ recommendations: RecommendationResponse[] }>('/api/v1/optimization/recommendations');
}

export async function generateRecommendation(modelId: string): Promise<RecommendationResponse> {
  return request<RecommendationResponse>('/api/v1/optimization/recommend', {
    method: 'POST',
    body: JSON.stringify({ model_id: modelId }),
  });
}

// Quality APIs
export async function fetchQualityDatasets(): Promise<{ datasets: QualityDatasetItem[] }> {
  return request<{ datasets: QualityDatasetItem[] }>('/api/v1/quality/datasets');
}

export async function fetchQualityEvaluations(): Promise<{ evaluations: QualityEvaluationResult[] }> {
  return request<{ evaluations: QualityEvaluationResult[] }>('/api/v1/quality/evaluations');
}

export async function evaluateQuality(modelId: string): Promise<QualityEvaluationResult> {
  return request<QualityEvaluationResult>('/api/v1/quality/evaluate', {
    method: 'POST',
    body: JSON.stringify({ model_id: modelId }),
  });
}

// Cost APIs
export async function calculateCost(payload: CostCalculationRequest): Promise<CostCalculationResponse> {
  return request<CostCalculationResponse>('/api/v1/optimization/cost/calculate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// Deployment APIs
export async function fetchDeployments(): Promise<{ total_count: number; deployments: DeploymentRecord[] }> {
  return request<{ total_count: number; deployments: DeploymentRecord[] }>('/api/v1/deployments');
}

export async function fetchActiveDeployment(): Promise<DeploymentRecord> {
  return request<DeploymentRecord>('/api/v1/deployments/active');
}

export async function fetchDeploymentsHealth(): Promise<DeploymentHealthSummary> {
  return request<DeploymentHealthSummary>('/api/v1/deployments/health');
}

export async function createDeployment(payload: DeploymentCreateRequest): Promise<DeploymentRecord> {
  return request<DeploymentRecord>('/api/v1/deployments', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function rollbackDeployment(deploymentId: string, reason?: string): Promise<RollbackResponse> {
  return request<RollbackResponse>(`/api/v1/deployments/${deploymentId}/rollback`, {
    method: 'POST',
    body: JSON.stringify({ reason: reason || 'Manual dashboard rollback' }),
  });
}

export async function fetchDeploymentMonitoring(deploymentId: string): Promise<DeploymentTelemetry> {
  return request<DeploymentTelemetry>(`/api/v1/deployments/${deploymentId}/monitoring`);
}

// Autonomous Agent APIs
export async function fetchAgentStatus(): Promise<AgentStatusResponse> {
  return request<AgentStatusResponse>('/api/v1/agent/status');
}

export async function startAgent(goal?: string): Promise<AgentStatusResponse> {
  return request<AgentStatusResponse>('/api/v1/agent/start', {
    method: 'POST',
    body: JSON.stringify({ goal: goal || 'Optimize inference latency on AWS Graviton3' }),
  });
}

export async function stopAgent(): Promise<AgentStatusResponse> {
  return request<AgentStatusResponse>('/api/v1/agent/stop', {
    method: 'POST',
  });
}

export async function fetchAgentDecisions(): Promise<{ decisions: AgentDecisionRecord[] }> {
  return request<{ decisions: AgentDecisionRecord[] }>('/api/v1/agent/decisions');
}

export async function fetchAgentHistory(): Promise<{ history: unknown[] }> {
  return request<{ history: unknown[] }>('/api/v1/agent/history');
}

// ---------------------------------------------------------------------------
// Arm Performix Official Integration API Types & Client Functions
// ---------------------------------------------------------------------------

export interface PerformixRunResult {
  performix_run_id: string;
  model_id: string;
  thread_count: number;
  batch_size: number;
  context_length: number;
  iterations: number;
  latency_p50_ms: number;
  latency_p90_ms: number;
  latency_p99_ms: number;
  ttft_ms: number;
  tokens_per_second: number;
  requests_per_second: number;
  cpu_percent: number;
  memory_used_mb: number;
  execution_status: string;
  retry_count: number;
  hardware_target: string;
  experiment_id?: string;
  deployment_id?: string;
  timestamp: string;
}

export interface MetricComparison {
  metric_name: string;
  armserve_value: number;
  performix_value: number;
  difference: number;
  variance_percent: number;
  consistency_percent: number;
  rating: string;
}

export interface PerformixComparisonResult {
  armserve_run_id: string;
  performix_run_id: string;
  model_id: string;
  hardware_target: string;
  metrics_comparison: MetricComparison[];
  overall_variance_percent: number;
  overall_consistency_score: number;
  verdict: string;
  timestamp: string;
}

export interface EvidenceReport {
  report_id: string;
  format: 'markdown' | 'json' | 'csv';
  content: string;
  generated_at: string;
  baseline_latency_p50_ms: number;
  optimized_latency_p50_ms: number;
  performance_gain_percent: number;
  performix_validated: boolean;
}

export async function runPerformixBenchmark(payload?: {
  model_id?: string;
  thread_count?: number;
  batch_size?: number;
  context_length?: number;
  iterations?: number;
}): Promise<PerformixRunResult> {
  return request<PerformixRunResult>('/api/v1/performix/run', {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  });
}

export async function fetchPerformixResults(): Promise<{ total_count: number; results: PerformixRunResult[] }> {
  return request<{ total_count: number; results: PerformixRunResult[] }>('/api/v1/performix/results');
}

export async function fetchPerformixComparison(
  armserveRunId: string = 'bm-run-001',
  performixRunId?: string
): Promise<PerformixComparisonResult> {
  const query = performixRunId
    ? `?armserve_run_id=${armserveRunId}&performix_run_id=${performixRunId}`
    : `?armserve_run_id=${armserveRunId}`;
  return request<PerformixComparisonResult>(`/api/v1/performix/comparison${query}`);
}

export async function fetchPerformixReport(format: 'markdown' | 'json' | 'csv' = 'markdown'): Promise<string> {
  const url = buildUrl(`/api/v1/performix/report?format=${format}`);
  const response = await fetch(url);
  return await response.text();
}

