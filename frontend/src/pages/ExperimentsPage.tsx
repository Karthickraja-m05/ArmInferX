import React, { useEffect, useState } from 'react';
import {
  fetchExperiments,
  createExperiment,
  fetchModels,
  ExperimentResponse,
  ModelResponse,
  ExperimentCreate,
} from '../services/api';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { FlaskConical, Plus, X } from 'lucide-react';

export const ExperimentsPage: React.FC = () => {
  const [experiments, setExperiments] = useState<ExperimentResponse[]>([]);
  const [models, setModels] = useState<ModelResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState<{
    name: string;
    model_id: string;
    max_latency_p99_ms: number;
    budget: number;
  }>({
    name: '',
    model_id: '',
    max_latency_p99_ms: 15,
    budget: 10,
  });
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [expsData, modelsData] = await Promise.all([
        fetchExperiments(),
        fetchModels(),
      ]);
      setExperiments(expsData);
      setModels(modelsData);
      if (modelsData.length > 0 && !formData.model_id) {
        setFormData((prev) => ({ ...prev, model_id: modelsData[0].id }));
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch experiments from database');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setModalError('Experiment name is required');
      return;
    }

    setSubmitting(true);
    setModalError(null);
    try {
      const payload: ExperimentCreate = {
        name: formData.name,
        model_id: formData.model_id || '00000000-0000-0000-0000-000000000000',
        constraints: {
          max_latency_p99_ms: formData.max_latency_p99_ms,
        },
        search_space: {
          runtimes: ['onnxruntime'],
          quantizations: ['INT8', 'FP16'],
        },
        budget: formData.budget,
      };

      await createExperiment(payload);
      setIsModalOpen(false);
      setFormData({ name: '', model_id: models[0]?.id || '', max_latency_p99_ms: 15, budget: 10 });
      await loadData();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setModalError(err.message);
      } else {
        setModalError('Failed to create experiment in database');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState message="Fetching Experiments from Database..." />;
  if (error) return <ErrorState title="Error Loading Experiments" message={error} onRetry={loadData} />;

  return (
    <div className="page-content">
      <div className="page-actions-bar">
        <div>
          <h2 className="section-title">Optimization Experiments</h2>
          <p className="section-subtitle">Real experiment records stored in backend database</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} style={{ marginRight: '0.4rem' }} />
          Create Experiment
        </button>
      </div>

      {experiments.length === 0 ? (
        <EmptyState
          icon={<FlaskConical size={40} />}
          title="No Experiments Created"
          description="The database currently contains no experiment records. Create an experiment to configure trial budgets and search spaces."
          actionLabel="Create Experiment"
          onAction={() => setIsModalOpen(true)}
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Experiment Name</th>
                <th>Status</th>
                <th>Trial Budget</th>
                <th>Model Version ID</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {experiments.map((exp) => (
                <tr key={exp.id}>
                  <td className="font-semibold">{exp.name}</td>
                  <td>
                    <span className="badge badge-emerald">{exp.status}</span>
                  </td>
                  <td>{exp.budget} trials</td>
                  <td className="code-text">{exp.model_id}</td>
                  <td className="text-muted">
                    {new Date(exp.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Experiment Modal */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3 className="modal-title">Create Experiment in Database</h3>
              <button className="btn-icon" onClick={() => setIsModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit}>
              <div className="form-group">
                <label className="form-label">Experiment Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. resnet50-graviton3-study"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              {models.length > 0 && (
                <div className="form-group">
                  <label className="form-label">Target Model</label>
                  <select
                    className="form-select"
                    value={formData.model_id}
                    onChange={(e) => setFormData({ ...formData, model_id: e.target.value })}
                  >
                    {models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.format})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Trial Budget</label>
                  <input
                    type="number"
                    className="form-input"
                    min={1}
                    max={100}
                    value={formData.budget}
                    onChange={(e) => setFormData({ ...formData, budget: parseInt(e.target.value) || 1 })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Max Latency P99 (ms)</label>
                  <input
                    type="number"
                    className="form-input"
                    min={1}
                    value={formData.max_latency_p99_ms}
                    onChange={(e) => setFormData({ ...formData, max_latency_p99_ms: parseFloat(e.target.value) || 1 })}
                  />
                </div>
              </div>

              {modalError && <p className="form-error">{modalError}</p>}

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Creating...' : 'Submit to Database'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
