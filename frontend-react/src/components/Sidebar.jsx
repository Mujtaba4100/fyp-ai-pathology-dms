import React from 'react';
import { 
  LayoutDashboard, 
  Upload, 
  Users, 
  Search, 
  MessageSquareCode, 
  BarChart2 
} from 'lucide-react';
import './Sidebar.css';

export default function Sidebar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'upload', label: 'Upload Report', icon: Upload },
    { id: 'patients', label: 'Patients', icon: Users },
    { id: 'search', label: 'Search', icon: Search },
    { id: 'assistant', label: 'AI Assistant', icon: MessageSquareCode },
    { id: 'analytics', label: 'Analytics', icon: BarChart2 },
  ];

  return (
    <aside className="pathiq-sidebar">
      {/* Brand Logo Header */}
      <div className="sidebar-brand">
        <div className="brand-icon-box">
          <div className="brand-inner-dot"></div>
        </div>
        <span className="brand-title">PathIQ</span>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-btn ${isActive ? 'nav-btn-active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <div className="nav-icon-container">
                <span className={`active-indicator-dot ${isActive ? 'visible' : ''}`} />
                <Icon size={18} className="nav-icon" />
              </div>
              <span className="nav-label">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Bottom User Profile */}
      <div className="sidebar-footer">
        <div className="user-profile-card">
          <div className="user-avatar"></div>
          <div className="user-info">
            <span className="user-name">Dr. A. Kanwal</span>
            <span className="user-role">Pathologist</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
