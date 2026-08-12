import { ENV } from '../config/env';

export interface HealthResponse {
  status: string;
  environment: string;
  database: string;
  timestamp: string;
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
  timestamp: string;
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

export interface ApiError {
  error_code: string;
  message: string;
  details?: unknown;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${ENV.API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      let errorData: ApiError | null = null;
      try {
        errorData = await response.json();
      } catch {
        // Fallback if response is not JSON
      }

      const errorMessage = errorData?.message || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (err: unknown) {
    if (err instanceof Error) {
      throw err;
    }
    throw new Error('An unknown network error occurred');
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

export async function fetchReadiness(): Promise<ReadinessResponse> {
  return request<ReadinessResponse>('/ready');
}

export async function fetchSystemInfo(): Promise<SystemInfoResponse> {
  return request<SystemInfoResponse>('/api/v1/system/info');
}

export async function fetchModels(): Promise<ModelResponse[]> {
  return request<ModelResponse[]>('/api/v1/models');
}

export async function registerModel(payload: ModelRegister): Promise<ModelResponse> {
  return request<ModelResponse>('/api/v1/models', {
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
