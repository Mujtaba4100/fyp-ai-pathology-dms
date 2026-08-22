/**
 * PathIQ API Service Layer
 * Connects to the FastAPI backend with offline fallback capabilities.
 */

const API_BASE_URL = 'http://localhost:8000/api';

export const apiService = {
  // Stats & Dashboard
  async getDashboardStats() {
    try {
      const res = await fetch(`${API_BASE_URL}/analytics/summary`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Backend unavailable, using PathIQ mock telemetry');
    }
    return {
      reports_processed: 1284,
      reports_this_week: 42,
      avg_ocr_time: '32.4s',
      abnormal_flags: 97,
      active_patients: 356,
      active_wards: 4,
    };
  },

  // Recent Reports
  async getRecentReports() {
    try {
      const res = await fetch(`${API_BASE_URL}/upload/list`);
      if (res.ok) {
        const data = await res.json();
        return data.files || [];
      }
    } catch (e) {
      console.warn('Backend unavailable, using PathIQ mock reports');
    }
    return [
      {
        id: 'rep-001',
        patient: 'Ayesha Raza',
        test: 'Complete Blood Count (CBC)',
        date: 'Aug 21',
        status: 'Processed',
        flag: 'Normal',
      },
      {
        id: 'rep-002',
        patient: 'Bilal Ahmed',
        test: 'Liver Function Test (LFT)',
        date: 'Aug 21',
        status: 'Processed',
        flag: 'High',
      },
      {
        id: 'rep-003',
        patient: 'Sana Tariq',
        test: 'Lipid Profile',
        date: 'Aug 20',
        status: 'Processed',
        flag: 'Normal',
      },
      {
        id: 'rep-004',
        patient: 'Usman Farooq',
        test: 'Kidney Function Test (KFT)',
        date: 'Aug 20',
        status: 'Extracting...',
        flag: 'Pending',
      },
      {
        id: 'rep-005',
        patient: 'Mehwish Iqbal',
        test: 'Urinalysis',
        date: 'Aug 19',
        status: 'Processed',
        flag: 'Low',
      },
    ];
  },

  // File Upload & OCR
  async uploadReport(file) {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Upload API unavailable, using simulated extraction');
    }
    return {
      status: 'success',
      filename: file.name,
      extracted_results: [
        { test: 'Serum Bilirubin (Total)', value: '2.41', unit: 'mg/dL', range: '0.2 – 1.2', flag: 'High' },
        { test: 'SGPT / ALT', value: '78', unit: 'U/L', range: '7 – 56', flag: 'High' },
        { test: 'SGOT / AST', value: '64', unit: 'U/L', range: '8 – 48', flag: 'High' },
        { test: 'Alkaline Phosphatase', value: '112', unit: 'U/L', range: '44 – 147', flag: 'Normal' },
        { test: 'Total Protein', value: '6.8', unit: 'g/dL', range: '6.0 – 8.3', flag: 'Normal' },
        { test: 'Albumin', value: '3.9', unit: 'g/dL', range: '3.5 – 5.0', flag: 'Normal' },
      ],
    };
  },

  // Clinical AI Assistant (RAG)
  async queryAssistant(question, conversationHistory = []) {
    try {
      const res = await fetch(`${API_BASE_URL}/chatbot/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, history: conversationHistory }),
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Chatbot API unavailable, using grounded mock response');
    }
    return {
      status: 'success',
      answer: "Across his last 3 reports, Bilal's liver markers show a rising trend. Bilirubin increased from 1.4 to 2.41 mg/dL and ALT from 52 to 78 U/L, both now above the normal reference range — consistent with worsening hepatic function.",
      source_documents: [
        { id: 'Report #AHDW-409773', date: 'Aug 21, 2026', test: 'LFT' },
        { id: 'Report #AHDW-402219', date: 'Jul 3, 2026', test: 'LFT' },
        { id: 'Report #AHDW-397004', date: 'Jun 18, 2026', test: 'CBC' },
      ],
      model: 'Llama-3.3-70B',
      patient_snapshot: {
        name: 'Bilal Ahmed',
        age: 42,
        gender: 'Male',
        mrn: 'MRN-88213',
        abnormal_flags_count: 2,
        trends: [
          { name: 'Bilirubin (Total)', change: '1.4 → 2.41 mg/dL', alert: true },
          { name: 'ALT (SGPT)', change: '52 → 78 U/L', alert: true },
          { name: 'Albumin', change: '4.0 → 3.9 g/dL', alert: false },
        ]
      }
    };
  },

  // Semantic Vector Search
  async semanticSearch(query) {
    try {
      const res = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('Search API fallback');
    }
    return {
      results: [
        {
          id: 'AHDW-409773',
          patient: 'Bilal Ahmed',
          test: 'Liver Function Test',
          similarity: 0.94,
          snippet: 'Serum Bilirubin Total: 2.41 mg/dL (High), SGPT/ALT: 78 U/L (High)...'
        },
        {
          id: 'AHDW-402219',
          patient: 'Bilal Ahmed',
          test: 'LFT Profile',
          similarity: 0.88,
          snippet: 'Serum Bilirubin Total: 1.4 mg/dL, SGPT/ALT: 52 U/L...'
        }
      ]
    };
  }
};
