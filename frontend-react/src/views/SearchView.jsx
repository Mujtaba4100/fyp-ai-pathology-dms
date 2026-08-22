import React, { useState } from 'react';
import { Search as SearchIcon, FileText, Database, Sparkles } from 'lucide-react';
import { apiService } from '../services/api';
import './SearchView.css';

export default function SearchView() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState([
    {
      id: 'AHDW-409773',
      patient: 'Bilal Ahmed',
      test: 'Liver Function Test (LFT)',
      date: 'Aug 21, 2026',
      similarity: 0.94,
      snippet: 'Serum Bilirubin Total: 2.41 mg/dL (High), SGPT/ALT: 78 U/L (High), Alkaline Phosphatase: 112 U/L...'
    },
    {
      id: 'AHDW-402219',
      patient: 'Bilal Ahmed',
      test: 'LFT Profile',
      date: 'Jul 3, 2026',
      similarity: 0.88,
      snippet: 'Serum Bilirubin Total: 1.4 mg/dL, SGPT/ALT: 52 U/L, Total Protein: 7.0 g/dL...'
    },
    {
      id: 'AHDW-397004',
      patient: 'Sana Tariq',
      test: 'Lipid Profile',
      date: 'Aug 20, 2026',
      similarity: 0.76,
      snippet: 'Cholesterol Total: 215 mg/dL (High), Triglycerides: 160 mg/dL, HDL: 45 mg/dL...'
    }
  ]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    const data = await apiService.semanticSearch(query);
    setIsSearching(false);
    if (data.results) setResults(data.results);
  };

  return (
    <div className="search-view-container">
      {/* Title Header */}
      <div className="search-header">
        <h1 className="search-title">Semantic Document Search</h1>
        <p className="search-subtitle">
          Query patient pathology history by clinical meaning using BioLORD-2023-M and pgvector
        </p>
      </div>

      {/* Main Search Box */}
      <form className="semantic-search-bar" onSubmit={handleSearch}>
        <SearchIcon size={18} className="search-bar-icon" />
        <input
          type="text"
          placeholder="e.g. 'Patients with elevated liver enzymes' or 'abnormal lipid panels'..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="search-main-input"
        />
        <button type="submit" className="btn-primary search-submit-btn">
          <span>Search Vector DB</span>
        </button>
      </form>

      {/* Suggested Query Chips */}
      <div className="search-suggestions-row">
        <span className="suggestions-label">Try searching:</span>
        <button className="chip-query" onClick={() => setQuery('Elevated bilirubin and transaminases')}>
          "Elevated bilirubin and transaminases"
        </button>
        <button className="chip-query" onClick={() => setQuery('Anemia indicators and low hemoglobin')}>
          "Anemia indicators and low hemoglobin"
        </button>
        <button className="chip-query" onClick={() => setQuery('Renal impairment with high creatinine')}>
          "Renal impairment with high creatinine"
        </button>
      </div>

      {/* Results List */}
      <div className="search-results-section">
        <div className="results-header-row">
          <span className="results-count-title">
            Retrieved Results ({results.length})
          </span>
          <span className="vector-metric-tag">
            <Database size={13} />
            <span>pgvector L2 Distance Ranking</span>
          </span>
        </div>

        <div className="results-cards-grid">
          {results.map((item, idx) => (
            <div key={idx} className="result-card card">
              <div className="result-card-top">
                <div className="result-doc-info">
                  <FileText size={16} className="doc-icon" />
                  <span className="result-patient-name">{item.patient}</span>
                  <span className="result-dash">—</span>
                  <span className="result-test-name">{item.test}</span>
                </div>
                <div className="similarity-badge">
                  <Sparkles size={12} />
                  <span>{Math.round(item.similarity * 100)}% Match</span>
                </div>
              </div>
              <p className="result-snippet-text">{item.snippet}</p>
              <div className="result-card-bottom">
                <span className="result-id-tag">Doc ID: {item.id}</span>
                <span className="result-date-tag">{item.date || 'Recent Report'}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
