import React, { useState, useEffect } from 'react';
import { generateSuggestedReply } from '../../../api';
import { useWebSocket } from '../../WebSocketProvider';
import CitationPopup from '../../CitationPopup';

function Toast({ message, type, onClose }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [message]);
  if (!message) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        bottom: 32,
        right: 32,
        background: type === 'error' ? '#ff4d4f' : '#222',
        color: '#fff',
        borderRadius: 8,
        padding: '12px 24px',
        fontSize: 15,
        zIndex: 9999,
        boxShadow: '0 4px 24px rgba(0,0,0,0.12)',
        minWidth: 180,
        outline: 'none',
      }}
      tabIndex={0}
    >
      {message}
      <button
        onClick={onClose}
        style={{ marginLeft: 16, color: '#fff', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700 }}
        aria-label="Close notification"
      >×</button>
    </div>
  );
}

export default function CopilotSidebar() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [suggested, setSuggested] = useState(null);
  const [tabUrl, setTabUrl] = useState('');
  const [citation, setCitation] = useState(null);
  // Toast state
  const [toast, setToast] = useState({ message: '', type: '' });

  // WebSocket context
  const ws = useWebSocket();

  // Get active tab URL (Chrome extension API)
  useEffect(() => {
    if (window.chrome && chrome.tabs) {
      chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        if (tabs[0]) setTabUrl(tabs[0].url || '');
      });
    }
  }, []);

  // Listen for WebSocket messages (real-time suggestions/citations)
  useEffect(() => {
    if (!ws.lastMessage) return;
    try {
      const msg = JSON.parse(ws.lastMessage);
      if (msg.type === 'suggestion') setSuggested(msg.data);
      if (msg.type === 'citation') setCitation(msg.data);
    } catch {}
  }, [ws.lastMessage]);

  // Toast notifications for connection status
  useEffect(() => {
    if (ws.status === 'open') setToast({ message: 'Connected', type: '' });
    if (ws.status === 'closed') setToast({ message: 'Connection lost. Trying to reconnect...', type: 'error' });
    if (ws.status === 'error') setToast({ message: 'WebSocket error. Please check your connection.', type: 'error' });
  }, [ws.status]);

  // Send input + context to backend via WebSocket
  const handleSuggest = (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuggested(null);
    setCitation(null);
    const payload = {
      type: 'suggest',
      data: {
        ticket_id: 'demo-ticket-1',
        user_id: 'demo-user-1',
        content: input,
        tab_url: tabUrl,
      }
    };
    ws.send(payload);
    setLoading(false);
  };

  return (
    <aside className="fixed top-0 right-0 w-[360px] h-full bg-white border-l border-gray-200 shadow-lg flex flex-col z-40">
      <header className="h-16 flex items-center px-6 border-b border-gray-100 bg-primary-blue relative">
        <span className="text-white text-lg font-semibold">AI Copilot</span>
        {/* Connection status indicator */}
        <span
          tabIndex={0}
          aria-label={`Connection status: ${ws.status}`}
          title={`Connection status: ${ws.status}`}
          style={{
            position: 'absolute',
            right: 16,
            top: 24,
            width: 14,
            height: 14,
            borderRadius: '50%',
            background: ws.status === 'open' ? '#16c60c' : ws.status === 'connecting' ? '#ffc107' : ws.status === 'closed' ? '#aaa' : '#ff4d4f',
            border: '2px solid #fff',
            outline: 'none',
            boxShadow: ws.status !== 'open' ? '0 0 0 2px #ff4d4f44' : undefined,
            transition: 'background 0.2s, box-shadow 0.2s',
            cursor: 'pointer',
          }}
          onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') e.target.click(); }}
        />
      </header>
      <div className="flex-1 overflow-y-auto p-4">
        <form onSubmit={handleSuggest} className="mb-4">
          <label className="block text-sm font-semibold mb-1">Customer Message</label>
          <textarea
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm mb-2"
            placeholder="Paste customer message or type query..."
            value={input}
            onChange={e => setInput(e.target.value)}
            rows={3}
          />
          <button
            type="submit"
            className="bg-primary-blue text-white rounded px-4 py-2 text-sm font-medium"
            disabled={loading || !input.trim()}
          >
            {loading ? 'Generating...' : 'Suggest Reply'}
          </button>
        </form>
        {error && <div className="text-red-500 text-sm mb-2">{error}</div>}
        {suggested && (
          <div className="mb-6 animate-fadein-slideup" style={{ animation: 'fadein-slideup 0.5s' }}>
            <div className="font-semibold text-base mb-2">Suggested Reply</div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 flex flex-col gap-1">
              <span className="text-sm">{suggested.reply_text}</span>
              {suggested.sources && suggested.sources.length > 0 && (
                <div className="mt-2">
                  <div className="font-semibold text-xs mb-1">Sources:</div>
                  <ul className="list-disc ml-5 text-xs">
                    {suggested.sources.map((src, idx) => (
                      <li key={idx}>
                        <a
                          href={src.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary-blue underline focus:outline-none focus:ring-2 focus:ring-blue-400 hover:text-blue-700"
                          tabIndex={0}
                          aria-label={`View source: ${src.title || src.url}`}
                        >
                          {src.title || src.url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {/* Show CitationPopup if citation data is present */}
              {citation && (
                <div className="mt-3 animate-fadein-slideup" style={{ animation: 'fadein-slideup 0.5s' }}>
                  <CitationPopup
                    excerpt={citation.excerpt}
                    confidence={citation.confidence}
                    lastUpdated={citation.last_updated}
                    sourceUrl={citation.source_url}
                  />
                </div>
              )}
            </div>
          </div>
        )}
        {/* Animations */}
        <style>{`
          @keyframes fadein-slideup {
            0% { opacity: 0; transform: translateY(24px); }
            100% { opacity: 1; transform: translateY(0); }
          }
          .animate-fadein-slideup { animation: fadein-slideup 0.5s; }
        `}</style>
        <div className="mb-6">
          <div className="font-semibold text-base mb-2">Customer Context</div>
          <div className="text-xs text-gray-700">Previous tickets, purchase history, account info...</div>
        </div>
        {/* Knowledge Base Search (future) */}
        <div>
          <div className="font-semibold text-base mb-2">Knowledge Base Search</div>
          <input className="w-full border border-gray-200 rounded px-3 py-2 text-sm mb-2" placeholder="Search KB..." disabled />
          <div className="space-y-1 text-xs text-gray-400">(Coming soon)</div>
        </div>
      </div>
    </aside>
  );
}
