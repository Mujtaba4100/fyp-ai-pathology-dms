import React, { useState } from 'react';
import { Users, FileText, Activity, AlertTriangle, ArrowRight } from 'lucide-react';
import './PatientsView.css';

export default function PatientsView({ onSelectPatient }) {
  const [patients] = useState([
    {
      id: 'P-101',
      name: 'Bilal Ahmed',
      age: 42,
      gender: 'Male',
      mrn: 'MRN-88213',
      ward: 'Ward 3 (Internal Med)',
      lastTest: 'Liver Function Test (LFT)',
      lastDate: 'Aug 21, 2026',
      flag: 'High',
      flagText: '2 abnormal flags'
    },
    {
      id: 'P-102',
      name: 'Ayesha Raza',
      age: 29,
      gender: 'Female',
      mrn: 'MRN-90412',
      ward: 'Ward 1 (General)',
      lastTest: 'Complete Blood Count (CBC)',
      lastDate: 'Aug 21, 2026',
      flag: 'Normal',
      flagText: 'All normal'
    },
    {
      id: 'P-103',
      name: 'Sana Tariq',
      age: 51,
      gender: 'Female',
      mrn: 'MRN-77319',
      ward: 'Ward 2 (Cardiology)',
      lastTest: 'Lipid Profile',
      lastDate: 'Aug 20, 2026',
      flag: 'Normal',
      flagText: 'Borderline cholesterol'
    },
    {
      id: 'P-104',
      name: 'Usman Farooq',
      age: 63,
      gender: 'Male',
      mrn: 'MRN-65481',
      ward: 'Ward 4 (Nephrology)',
      lastTest: 'Kidney Function Test (KFT)',
      lastDate: 'Aug 20, 2026',
      flag: 'Pending',
      flagText: 'Processing OCR'
    },
    {
      id: 'P-105',
      name: 'Mehwish Iqbal',
      age: 38,
      gender: 'Female',
      mrn: 'MRN-81190',
      ward: 'Ward 1 (General)',
      lastTest: 'Urinalysis',
      lastDate: 'Aug 19, 2026',
      flag: 'Low',
      flagText: '1 abnormal flag'
    }
  ]);

  return (
    <div className="patients-view-container">
      <div className="patients-header">
        <h1 className="patients-title">Active Patients Directory</h1>
        <p className="patients-subtitle">356 active patient profiles indexed with EMR records</p>
      </div>

      <div className="patients-table-card card">
        <div className="table-responsive">
          <table className="patients-table">
            <thead>
              <tr>
                <th>Patient Details</th>
                <th>Ward Location</th>
                <th>Recent Pathology Test</th>
                <th>Latest Date</th>
                <th>Status / Flags</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p) => (
                <tr key={p.id}>
                  <td>
                    <div className="patient-cell-info">
                      <span className="p-cell-name">{p.name}</span>
                      <span className="p-cell-sub">{p.age}y · {p.gender} · {p.mrn}</span>
                    </div>
                  </td>
                  <td className="ward-cell">{p.ward}</td>
                  <td className="test-cell">{p.lastTest}</td>
                  <td className="date-cell">{p.lastDate}</td>
                  <td>
                    <span className={`badge ${
                      p.flag === 'High' ? 'badge-high' :
                      p.flag === 'Low' ? 'badge-low' :
                      p.flag === 'Normal' ? 'badge-normal' : 'badge-pending'
                    }`}>
                      {p.flagText}
                    </span>
                  </td>
                  <td>
                    <button 
                      className="btn-secondary inspect-btn"
                      onClick={() => onSelectPatient && onSelectPatient(p)}
                    >
                      <span>Query AI</span>
                      <ArrowRight size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
