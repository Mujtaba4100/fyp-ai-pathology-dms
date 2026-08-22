import React from 'react';
import './StatCard.css';

export default function StatCard({ label, value, subtext, subtextColor }) {
  return (
    <div className="stat-card card">
      <span className="stat-label">{label}</span>
      <div className="stat-value-row">
        <span className="stat-value">{value}</span>
      </div>
      <span className={`stat-subtext ${subtextColor || ''}`}>{subtext}</span>
    </div>
  );
}
