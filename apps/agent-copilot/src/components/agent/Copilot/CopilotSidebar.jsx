import React, { useState, useEffect } from 'react';
import { Sparkles, Copy, Check, X, Wifi, WifiOff, Send, Search, User, FileText, ExternalLink } from 'lucide-react';
import { generateSuggestedReply } from '../../../api';
import { useWebSocket } from '../../WebSocketProvider';
import CitationPopup from '../../CitationPopup';

function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

function Toast({ message, type, onClose }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [message, onClose]);
  if (!message) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'fixed bottom-8 right-8 z-[9999]',
        'px-4 py-3 rounded-xl shadow-lg',
        'text-white text-sm font-medium',
        'flex items-center gap-3',
        'animate-fade-in-up',
        type === 'error' ? 'bg-red-500' : 'bg-gray-900',
      )}
    >
      {type === 'error' ? <WifiOff className="w-4 h-4 flex-shrink-0" /> : <Wifi className="w-4 h-4 flex-shrink-0" />}
      {message}
      <button
        onClick={onClose}
        className="ml-2 hover:bg-white/20 rounded p-0.5 transition-colors"
        aria-label="Close notification"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

function ConnectionDot({ status }) {
  const colors = {
    open: 'bg-emerald-400',
    connecting: 'bg-amber-400 animate-pulse',
    closed: 'bg-gray-400',
    error: 'bg-red-400',
  };
  return (
    <span
      tabIndex={0}
      aria-label={`Connection status: ${status}`}
      title={`Connection: ${status}`}
      className={cn(
        'w-2.5 h-2.5 rounded-full',
        'ring-2 ring-white/30',
        'transition-colors duration-200',
        colors[status] || colors.closed,
      )}
    />
  );
}

export default function CopilotSidebar() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [suggested, setSuggested] = useState(null);
  const [tabUrl, setTabUrl] = useState('');
  const [citation, setCitation] = useState(null);
  const [copied, setCopied] = useState(false);
  const [toast, setToast] = useState({ message: '', type: '' });

  const ws = useWebSocket();

  useEffect(() => {
    if (window.chrome && chrome.tabs) {
      chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        if (tabs[0]) setTabUrl(tabs[0].url || '');
      });
    }
  }, []);

  useEffect(() => {
    if (!ws.lastMessage) return;
    try {
      const msg = JSON.parse(ws.lastMessage);
      if (msg.type === 'suggestion') setSuggested(msg.data);
      if (msg.type === 'citation') setCitation(msg.data);
    } catch {}
  }, [ws.lastMessage]);

  useEffect(() => {
    if (ws.status === 'open') setToast({ message: 'Connected', type: '' });
    if (ws.status === 'closed') setToast({ message: 'Connection lost. Reconnecting...', type: 'error' });
    if (ws.status === 'error') setToast({ message: 'Connection error', type: 'error' });
  }, [ws.status]);

  const handleCopy = async () => {
    if (!suggested?.reply_text) return;
    await navigator.clipboard.writeText(suggested.reply_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSuggest = (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuggested(null);
    setCitation(null);
    ws.send({
      type: 'suggest',
      data: {
        ticket_id: 'demo-ticket-1',
        user_id: 'demo-user-1',
        content: input,
        tab_url: tabUrl,
      },
    });
    setLoading(false);
  };

  return (
    <aside className={cn(
      'fixed top-0 right-0 w-[360px] h-full z-40',
      'bg-white dark:bg-slate-900',
      'border-l border-gray-200 dark:border-slate-700',
      'shadow-xl flex flex-col',
    )}>
      {/* Header */}
      <header className={cn(
        'px-5 py-3.5 flex items-center justify-between',
        'bg-gradient-to-r from-brand-500 to-brand-600',
        'dark:from-brand-600 dark:to-brand-800',
      )}>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-white text-sm font-semibold leading-tight">AI Copilot</h1>
            <p className="text-white/60 text-[10px]">Context-aware assistance</p>
          </div>
        </div>
        <ConnectionDot status={ws.status} />
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5 scrollbar-thin">
        {/* Input form */}
        <form onSubmit={handleSuggest}>
          <label className="block text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
            Customer Message
          </label>
          <textarea
            className={cn(
              'w-full rounded-xl px-3.5 py-2.5 text-sm resize-none',
              'bg-gray-50 dark:bg-slate-800',
              'border border-gray-200 dark:border-slate-700',
              'text-gray-900 dark:text-slate-100',
              'placeholder:text-gray-400 dark:placeholder:text-slate-500',
              'focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500',
              'transition-all duration-200',
            )}
            placeholder="Paste customer message or type query..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={3}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className={cn(
              'mt-2 w-full flex items-center justify-center gap-2',
              'rounded-xl px-4 py-2.5 text-sm font-medium',
              'bg-brand-500 text-white',
              'hover:bg-brand-600 active:scale-[0.98]',
              'disabled:opacity-40 disabled:cursor-not-allowed',
              'transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2',
            )}
          >
            <Send className="w-4 h-4" />
            {loading ? 'Generating...' : 'Suggest Reply'}
          </button>
        </form>

        {error && (
          <div className="px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Suggested Reply */}
        {suggested && (
          <div className="animate-fade-in-up">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                Suggested Reply
              </span>
              <button
                onClick={handleCopy}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium',
                  'transition-all duration-200',
                  copied
                    ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700',
                )}
                aria-label="Copy reply"
              >
                {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <div className={cn(
              'rounded-xl p-4',
              'bg-gray-50 dark:bg-slate-800',
              'border border-gray-200 dark:border-slate-700',
              'shadow-sm',
            )}>
              <p className="text-sm text-gray-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                {suggested.reply_text}
              </p>
              {suggested.sources && suggested.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-slate-700">
                  <span className="text-[10px] font-semibold text-gray-400 dark:text-slate-500 uppercase tracking-wider">
                    Sources
                  </span>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {suggested.sources.map((src, idx) => (
                      <a
                        key={idx}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={cn(
                          'inline-flex items-center gap-1',
                          'text-[10px] font-medium px-2 py-0.5 rounded-full',
                          'bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-300',
                          'hover:bg-brand-100 dark:hover:bg-brand-900/50',
                          'transition-colors',
                        )}
                        aria-label={`View source: ${src.title || src.url}`}
                      >
                        <ExternalLink className="w-2.5 h-2.5" />
                        {src.title || src.url}
                      </a>
                    ))}
                  </div>
                </div>
              )}
              {citation && (
                <div className="mt-3 animate-fade-in-up">
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

        {/* Customer Context */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <User className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
            <span className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              Customer Context
            </span>
          </div>
          <div className={cn(
            'rounded-xl p-3',
            'bg-gray-50 dark:bg-slate-800',
            'border border-gray-200 dark:border-slate-700',
          )}>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              Previous tickets, purchase history, account info...
            </p>
          </div>
        </div>

        {/* Knowledge Base Search */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
            <span className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              Knowledge Base
            </span>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
            <input
              className={cn(
                'w-full rounded-xl pl-9 pr-3 py-2.5 text-sm',
                'bg-gray-50 dark:bg-slate-800',
                'border border-gray-200 dark:border-slate-700',
                'text-gray-900 dark:text-slate-100',
                'placeholder:text-gray-400 dark:placeholder:text-slate-500',
                'focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500',
                'transition-all duration-200',
              )}
              placeholder="Search knowledge base..."
              disabled
            />
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast.message && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast({ message: '', type: '' })}
        />
      )}
    </aside>
  );
}
