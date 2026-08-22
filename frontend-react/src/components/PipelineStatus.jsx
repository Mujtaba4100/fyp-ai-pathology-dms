import React from 'react';
import './PipelineStatus.css';

export default function PipelineStatus() {
  const steps = [
    { label: 'OCR Extraction', completed: true },
    { label: 'Structured Parsing (LLM)', completed: true },
    { label: 'Clinical Embeddings', completed: true },
    { label: 'Vector Indexing', completed: true },
    { label: 'Ready for Query', completed: false },
  ];

  return (
    <div className="pipeline-status-card card">
      <div className="pipeline-header">
        <h3 className="pipeline-title">Pipeline Status</h3>
        <p className="pipeline-subtitle">Live processing for Bilal Ahmed — LFT</p>
      </div>

      {/* Stepper list */}
      <div className="pipeline-steps">
        {steps.map((step, idx) => (
          <div key={idx} className="pipeline-step-item">
            <span className={`step-dot ${step.completed ? 'completed' : 'pending'}`} />
            <span className={`step-label ${step.completed ? 'label-completed' : 'label-pending'}`}>
              {step.label}
            </span>
          </div>
        ))}
      </div>

      {/* Divider */}
      <div className="pipeline-divider" />

      {/* Model Stack Box */}
      <div className="model-stack-section">
        <span className="model-stack-heading">Model Stack</span>
        <div className="model-stack-list">
          <div className="model-stack-row">
            <span className="model-role">OCR</span>
            <span className="model-dash">—</span>
            <span className="model-val">DeepSeek-OCR-2 (FP16)</span>
          </div>
          <div className="model-stack-row">
            <span className="model-role">Extraction</span>
            <span className="model-dash">—</span>
            <span className="model-val">Llama-3.3-70B</span>
          </div>
          <div className="model-stack-row">
            <span className="model-role">Embeddings</span>
            <span className="model-dash">—</span>
            <span className="model-val">BioLORD-2023-M</span>
          </div>
          <div className="model-stack-row">
            <span className="model-role">Store</span>
            <span className="model-dash">—</span>
            <span className="model-val">PostgreSQL + pgvector</span>
          </div>
        </div>
      </div>
    </div>
  );
}
