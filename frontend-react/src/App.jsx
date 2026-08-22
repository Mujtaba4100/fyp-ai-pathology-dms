import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import DashboardView from './views/DashboardView';
import UploadView from './views/UploadView';
import AssistantView from './views/AssistantView';
import SearchView from './views/SearchView';
import PatientsView from './views/PatientsView';
import './styles/global.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderActiveView = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardView onNavigate={(tab) => setActiveTab(tab)} />;
      case 'upload':
        return <UploadView onSaveSuccess={() => setActiveTab('dashboard')} />;
      case 'assistant':
        return <AssistantView />;
      case 'search':
        return <SearchView />;
      case 'patients':
      case 'analytics':
        return <PatientsView onSelectPatient={() => setActiveTab('assistant')} />;
      default:
        return <DashboardView onNavigate={(tab) => setActiveTab(tab)} />;
    }
  };

  return (
    <div className="app-layout">
      {/* Left PathIQ Sidebar */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Dynamic View Content */}
      <main className="main-content">
        {renderActiveView()}
      </main>
    </div>
  );
}
