import React, { useState, useEffect } from 'react';
import { Search as SearchIcon, Plus, ArrowRight } from 'lucide-react';
import StatCard from '../components/StatCard';
import PipelineStatus from '../components/PipelineStatus';
import { apiService } from '../services/api';
import './DashboardView.css';

export default function DashboardView({ onNavigate }) {
  const [stats, setStats] = useState({
    reports_processed: 1284,
    reports_this_week: 42,
    avg_ocr_time: '32.4s',
    abnormal_flags: 97,
    active_patients: 356,
    active_wards: 4,
  });

  const [reports, setReports] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    async function loadData() {
      const s = await apiService.getDashboardStats();
      const r = await apiService.getRecentReports();
      setStats(s);
      setReports(r);
    }
    loadData();
  }, []);

  const getBadgeClass = (flag) => {
    switch ((flag || '').toLowerCase()) {
      case 'normal': return 'badge-normal';
      case 'high': return 'badge-high';
      case 'low': return 'badge-low';
      case 'pending': return 'badge-pending';
      default: return 'badge-pending';
    }
  };

  return (
    <div className="dashboard-view-container">
      {/* Top Header Bar */}
      <header className="dash-top-header">
        <div className="dash-greeting">
          <h1 className="greeting-title">Good morning, Dr. Kanwal</h1>
          <p className="greeting-subtitle">Here's what's happening across your lab today</p>
        </div>

        <div className="dash-top-actions">
          <div className="header-search-box">
            <SearchIcon size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search patients, reports..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>
          <button 
            className="btn-primary" 
            onClick={() => onNavigate('upload')}
          >
            <Plus size={16} />
            <span>Upload Report</span>
          </button>
        </div>
      </header>

      {/* 4 Stat Metrics Cards */}
      <section className="dash-stats-grid">
        <StatCard
          label="Reports Processed"
          value={stats.reports_processed.toLocaleString()}
          subtext={`+${stats.reports_this_week} this week`}
          subtextColor="green"
        />
        <StatCard
          label="Avg. OCR Time"
          value={stats.avg_ocr_time}
          subtext="per report"
        />
        <StatCard
          label="Abnormal Flags"
          value={stats.abnormal_flags}
          subtext="needs review"
          subtextColor="amber"
        />
        <StatCard
          label="Active Patients"
          value={stats.active_patients}
          subtext={`across ${stats.active_wards} wards`}
        />
      </section>

      {/* Main Content Grid: Recent Reports (Left) & Pipeline Status (Right) */}
      <section className="dash-main-grid">
        {/* Left Column: Recent Reports Table */}
        <div className="recent-reports-card card">
          <div className="card-header-row">
            <div className="header-left">
              <h3 className="section-heading">Recent Reports</h3>
            </div>
            <button className="view-all-btn" onClick={() => onNavigate('patients')}>
              <span>View all</span>
              <ArrowRight size={13} />
            </button>
          </div>

          <div className="table-responsive">
            <table className="pathology-table">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Test</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Flag</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((row) => (
                  <tr key={row.id}>
                    <td className="patient-cell-name">{row.patient}</td>
                    <td className="test-cell-name">{row.test}</td>
                    <td className="date-cell">{row.date}</td>
                    <td className="status-cell">{row.status}</td>
                    <td>
                      <span className={`badge ${getBadgeClass(row.flag)}`}>
                        {row.flag}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Pipeline Status */}
        <div className="pipeline-widget-container">
          <PipelineStatus />
        </div>
      </section>
    </div>
  );
}
