import React, { useEffect, useState } from 'react';
import { fetchModels, registerModel, ModelResponse, ModelRegister } from '../services/api';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Box, Plus, X } from 'lucide-react';

export const ModelsPage: React.FC = () => {
  const [models, setModels] = useState<ModelResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState<ModelRegister>({
    name: '',
    source: 'HuggingFace',
    format: 'ONNX',
    quantization: 'NONE',
  });
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadModels = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchModels();
      setModels(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch models from database');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setModalError('Model name is required');
      return;
    }

    setSubmitting(true);
    setModalError(null);
    try {
      await registerModel(formData);
      setIsModalOpen(false);
      setFormData({ name: '', source: 'HuggingFace', format: 'ONNX', quantization: 'NONE' });
      await loadModels();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setModalError(err.message);
      } else {
        setModalError('Failed to register model in database');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState message="Fetching Model Registry from Database..." />;
  if (error) return <ErrorState title="Error Loading Models" message={error} onRetry={loadModels} />;

  return (
    <div className="page-content">
      <div className="page-actions-bar">
        <div>
          <h2 className="section-title">Model Registry Records</h2>
          <p className="section-subtitle">Real model entries stored in backend database</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={16} style={{ marginRight: '0.4rem' }} />
          Register Model
        </button>
      </div>

      {models.length === 0 ? (
        <EmptyState
          icon={<Box size={40} />}
          title="No Models Registered"
          description="The database registry currently contains no model entries. Register your first model to get started."
          actionLabel="Register Model"
          onAction={() => setIsModalOpen(true)}
        />
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Model Name</th>
                <th>Format</th>
                <th>Source</th>
                <th>Quantization</th>
                <th>Storage URI</th>
                <th>Registered At</th>
              </tr>
            </thead>
            <tbody>
              {models.map((model) => (
                <tr key={model.id}>
                  <td className="font-semibold">{model.name}</td>
                  <td>
                    <span className="badge badge-blue">{model.format}</span>
                  </td>
                  <td>{model.source}</td>
                  <td>
                    <span className="badge badge-purple">{model.quantization}</span>
                  </td>
                  <td className="code-text">{model.storage_uri}</td>
                  <td className="text-muted">
                    {new Date(model.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Registration Modal */}
      {isModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3 className="modal-title">Register Model in Database</h3>
              <button className="btn-icon" onClick={() => setIsModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleFormSubmit}>
              <div className="form-group">
                <label className="form-label">Model Identifier / Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. llama3-8b-arm"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Source Repository</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Meta AI / HuggingFace"
                  value={formData.source}
                  onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Format</label>
                  <select
                    className="form-select"
                    value={formData.format}
                    onChange={(e) => setFormData({ ...formData, format: e.target.value })}
                  >
                    <option value="ONNX">ONNX</option>
                    <option value="PYTORCH">PyTorch</option>
                    <option value="GGUF">GGUF</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Quantization</label>
                  <select
                    className="form-select"
                    value={formData.quantization}
                    onChange={(e) => setFormData({ ...formData, quantization: e.target.value })}
                  >
                    <option value="NONE">FP32 (None)</option>
                    <option value="FP16">FP16</option>
                    <option value="INT8">INT8</option>
                  </select>
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
                  {submitting ? 'Registering...' : 'Submit to Database'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
