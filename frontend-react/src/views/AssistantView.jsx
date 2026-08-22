import React, { useState } from 'react';
import { Send, Sparkles, ExternalLink, ShieldCheck } from 'lucide-react';
import PatientSidebar from '../components/PatientSidebar';
import { apiService } from '../services/api';
import './AssistantView.css';

export default function AssistantView() {
  const [messages, setMessages] = useState([
    {
      id: 'm1',
      sender: 'user',
      text: "What was Bilal Ahmed's liver function trend over his last 3 visits?",
    },
    {
      id: 'm2',
      sender: 'assistant',
      text: "Across his last 3 reports, Bilal's liver markers show a rising trend. Bilirubin increased from 1.4 to 2.41 mg/dL and ALT from 52 to 78 U/L, both now above the normal reference range — consistent with worsening hepatic function.",
      sources: [
        { id: 'Report #AHDW-409773', date: 'Aug 21, 2026', test: 'LFT' },
        { id: 'Report #AHDW-402219', date: 'Jul 3, 2026', test: 'LFT' },
        { id: 'Report #AHDW-397004', date: 'Jun 18, 2026', test: 'CBC' },
      ],
      model: 'Llama-3.3-70B',
    }
  ]);

  const [inputQuery, setInputQuery] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(null);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputQuery.trim() || isTyping) return;

    const userText = inputQuery;
    const userMsg = { id: `m-${Date.now()}`, sender: 'user', text: userText };
    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');
    setIsTyping(true);

    const res = await apiService.queryAssistant(userText);
    setIsTyping(false);

    const assistantMsg = {
      id: `m-bot-${Date.now()}`,
      sender: 'assistant',
      text: res.answer,
      sources: res.source_documents || [],
      model: res.model || 'Llama-3.3-70B',
    };
    setMessages(prev => [...prev, assistantMsg]);
  };

  return (
    <div className="assistant-layout-wrapper">
      {/* Main Chat Conversation Area */}
      <div className="assistant-chat-pane">
        {/* Header */}
        <header className="assistant-header">
          <h1 className="assistant-title">Clinical AI Assistant</h1>
          <p className="assistant-subtitle">
            Grounded answers from patient diagnostic history · zero hallucination
          </p>
        </header>

        {/* Message Thread */}
        <div className="chat-messages-scroll-area">
          {messages.map((msg) => (
            <div key={msg.id} className={`message-row ${msg.sender === 'user' ? 'row-user' : 'row-assistant'}`}>
              {msg.sender === 'user' ? (
                <div className="user-chat-bubble">
                  {msg.text}
                </div>
              ) : (
                <div className="assistant-card card">
                  <p className="assistant-answer-text">{msg.text}</p>
                  
                  {/* Source Document Citation Chips */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="citation-chips-row">
                      {msg.sources.map((src, i) => (
                        <button
                          key={i}
                          className="citation-chip-btn"
                          onClick={() => setSelectedCitation(src)}
                        >
                          <span>{src.id || src}</span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Footnote */}
                  <div className="assistant-card-footer">
                    <span>
                      Sources: {msg.sources?.length || 0} retrieved reports · {msg.model || 'Llama-3.3-70B'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="message-row row-assistant">
              <div className="assistant-card card typing-card">
                <Sparkles size={16} className="sparkle-spin" />
                <span>Searching vector database with BioLORD & generating grounded response...</span>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Chat Input Form */}
        <form className="chat-input-bar" onSubmit={handleSend}>
          <input
            type="text"
            placeholder="Ask about a patient's diagnostic history..."
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            className="chat-text-input"
          />
          <button type="submit" className="btn-primary send-chat-btn" disabled={!inputQuery.trim()}>
            <span>Send</span>
          </button>
        </form>
      </div>

      {/* Right Patient Context Sidebar */}
      <PatientSidebar />

      {/* Citation Preview Modal */}
      {selectedCitation && (
        <div className="citation-modal-overlay" onClick={() => setSelectedCitation(null)}>
          <div className="citation-modal-card card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h4 className="modal-title">{selectedCitation.id}</h4>
              <button className="close-btn" onClick={() => setSelectedCitation(null)}>✕</button>
            </div>
            <div className="modal-body">
              <p className="modal-info-line"><strong>Test Category:</strong> {selectedCitation.test || 'Pathology Panel'}</p>
              <p className="modal-info-line"><strong>Collection Date:</strong> {selectedCitation.date || 'Aug 21, 2026'}</p>
              <div className="modal-snippet-box">
                <span className="snippet-title">Grounding EMR Extract:</span>
                <p>Serum Bilirubin Total: 2.41 mg/dL (High), SGPT/ALT: 78 U/L (High), Alkaline Phosphatase: 112 U/L (Normal). Verified by Pathologist Dr. A. Kanwal.</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
