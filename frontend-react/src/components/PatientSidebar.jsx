import React from 'react';
import './PatientSidebar.css';

export default function PatientSidebar({ patientData }) {
  const patient = patientData || {
    name: 'Bilal Ahmed',
    age: 42,
    gender: 'Male',
    mrn: 'MRN-88213',
    flagsCount: 2,
    reports: [
      { type: 'LFT', date: 'Aug 21, 2026', id: 'AHDW-409773' },
      { type: 'LFT', date: 'Jul 3, 2026', id: 'AHDW-402219' },
      { type: 'CBC', date: 'Jun 18, 2026', id: 'AHDW-397004' },
    ],
    trends: [
      { name: 'Bilirubin (Total)', change: '1.4 → 2.41 mg/dL', alert: true },
      { name: 'ALT (SGPT)', change: '52 → 78 U/L', alert: true },
      { name: 'Albumin', change: '4.0 → 3.9 g/dL', alert: false },
    ]
  };

  return (
    <aside className="patient-context-sidebar">
      {/* Patient Profile Header */}
      <div className="patient-header">
        <div className="patient-avatar-box"></div>
        <div className="patient-meta">
          <h4 className="patient-name">{patient.name}</h4>
          <span className="patient-demographics">
            {patient.age}y · {patient.gender} · {patient.mrn}
          </span>
        </div>
      </div>

      {/* Abnormal Alert Pill */}
      {patient.flagsCount > 0 && (
        <div className="active-flags-pill">
          {patient.flagsCount} abnormal flags active
        </div>
      )}

      {/* Divider */}
      <div className="sidebar-section-divider" />

      {/* Retrieved Reports */}
      <div className="sidebar-section">
        <span className="section-title">Retrieved Reports</span>
        <div className="retrieved-reports-list">
          {patient.reports.map((rep, idx) => (
            <div key={idx} className="retrieved-report-card">
              <div className="rep-row-top">
                <span className="rep-type-date">{rep.type} — {rep.date}</span>
              </div>
              <span className="rep-id">{rep.id}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="sidebar-section-divider" />

      {/* Trend Snapshot */}
      <div className="sidebar-section">
        <span className="section-title">Trend Snapshot</span>
        <div className="trends-list">
          {patient.trends.map((tr, idx) => (
            <div key={idx} className="trend-item">
              <span className="trend-name">{tr.name}</span>
              <span className={`trend-change ${tr.alert ? 'trend-alert' : 'trend-normal'}`}>
                {tr.change}
              </span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
