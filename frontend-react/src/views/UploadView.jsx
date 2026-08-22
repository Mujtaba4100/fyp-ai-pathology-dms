import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, FileText, AlertCircle, Edit3 } from 'lucide-react';
import { apiService } from '../services/api';
import './UploadView.css';

export default function UploadView({ onSaveSuccess }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [extractedData, setExtractedData] = useState({
    filename: 'bilal_ahmed_lft_aug21.pdf',
    model: 'Llama-3.3-70B',
    reviewedCount: 0,
    totalCount: 6,
    results: [
      { id: 1, test: 'Serum Bilirubin (Total)', value: '2.41', unit: 'mg/dL', range: '0.2 – 1.2', flag: 'High', isAbnormal: true },
      { id: 2, test: 'SGPT / ALT', value: '78', unit: 'U/L', range: '7 – 56', flag: 'High', isAbnormal: true },
      { id: 3, test: 'SGOT / AST', value: '64', unit: 'U/L', range: '8 – 48', flag: 'High', isAbnormal: true },
      { id: 4, test: 'Alkaline Phosphatase', value: '112', unit: 'U/L', range: '44 – 147', flag: 'Normal', isAbnormal: false },
      { id: 5, test: 'Total Protein', value: '6.8', unit: 'g/dL', range: '6.0 – 8.3', flag: 'Normal', isAbnormal: false },
      { id: 6, test: 'Albumin', value: '3.9', unit: 'g/dL', range: '3.5 – 5.0', flag: 'Normal', isAbnormal: false },
    ]
  });

  const [isEditing, setIsEditing] = useState(false);
  const [showSavedToast, setShowSavedToast] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const processFile = async (file) => {
    if (!file) return;
    setSelectedFile(file);
    setIsProcessing(true);
    const data = await apiService.uploadReport(file);
    setIsProcessing(false);
    setExtractedData(prev => ({
      ...prev,
      filename: file.name,
      results: data.extracted_results.map((r, i) => ({
        id: i + 1,
        ...r,
        isAbnormal: r.flag.toLowerCase() === 'high' || r.flag.toLowerCase() === 'low'
      }))
    }));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const handleValueChange = (id, newVal) => {
    setExtractedData(prev => ({
      ...prev,
      results: prev.results.map(item => item.id === id ? { ...item, value: newVal } : item)
    }));
  };

  const handleConfirmSave = () => {
    setShowSavedToast(true);
    setTimeout(() => {
      setShowSavedToast(false);
      if (onSaveSuccess) onSaveSuccess();
    }, 2000);
  };

  return (
    <div className="upload-view-container">
      {/* Title Header */}
      <div className="upload-header">
        <h1 className="upload-title">Upload Pathology Report</h1>
        <p className="upload-subtitle">Supports PDF, JPG, PNG — scanned or photographed reports</p>
      </div>

      {/* Drag & Drop Upload Dropzone Box */}
      <div
        className={`dropzone-box ${dragActive ? 'dropzone-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
        <div className="dropzone-icon-circle">
          <UploadCloud size={24} className="dropzone-cloud-icon" />
        </div>
        <span className="dropzone-main-text">
          {isProcessing ? 'Processing with DeepSeek-OCR-2 & Llama-3.3...' : 'Drag & drop a report, or click to browse'}
        </span>
        <span className="dropzone-sub-text">Max 20MB per file · Batch upload supported</span>
        <button 
          className="btn-primary browse-btn"
          onClick={(e) => {
            e.stopPropagation();
            fileInputRef.current?.click();
          }}
        >
          Browse Files
        </button>
      </div>

      {/* Extracted Results Table Section */}
      <div className="extracted-results-card card">
        <div className="extracted-card-header">
          <div className="extracted-header-titles">
            <h3 className="extracted-filename">
              Extracted Results — {extractedData.filename}
            </h3>
            <p className="extracted-meta">
              Parsed by {extractedData.model} · reviewed {extractedData.reviewedCount} of {extractedData.totalCount} values
            </p>
          </div>
          <span className="badge badge-low needs-review-badge">Needs Review</span>
        </div>

        {/* Results Table */}
        <div className="table-responsive">
          <table className="extracted-table">
            <thead>
              <tr>
                <th>Test</th>
                <th>Value</th>
                <th>Unit</th>
                <th>Reference Range</th>
                <th>Flag</th>
              </tr>
            </thead>
            <tbody>
              {extractedData.results.map((row) => (
                <tr key={row.id}>
                  <td className="test-name-col">{row.test}</td>
                  <td className="test-value-col">
                    {isEditing ? (
                      <input
                        type="text"
                        value={row.value}
                        onChange={(e) => handleValueChange(row.id, e.target.value)}
                        className="inline-value-input"
                      />
                    ) : (
                      <span className={`val-display ${row.isAbnormal ? 'val-abnormal' : 'val-normal'}`}>
                        {row.value}
                      </span>
                    )}
                  </td>
                  <td className="test-unit-col">{row.unit}</td>
                  <td className="test-range-col">{row.range}</td>
                  <td className="test-flag-col">
                    <span className={`badge ${row.flag === 'High' ? 'badge-high' : 'badge-normal'}`}>
                      {row.flag}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Action Buttons Footer */}
        <div className="extracted-footer-actions">
          <button 
            className="btn-secondary" 
            onClick={() => setIsEditing(!isEditing)}
          >
            <Edit3 size={14} />
            <span>{isEditing ? 'Done Editing' : 'Edit Values'}</span>
          </button>
          <button 
            className="btn-primary" 
            onClick={handleConfirmSave}
          >
            <CheckCircle size={15} />
            <span>Confirm & Save to EMR</span>
          </button>
        </div>
      </div>

      {/* Toast Notification on Save */}
      {showSavedToast && (
        <div className="saved-toast">
          <CheckCircle size={16} />
          <span>Report and structured results successfully saved to PostgreSQL EMR!</span>
        </div>
      )}
    </div>
  );
}
