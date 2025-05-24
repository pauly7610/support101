import React from 'react';

export default function ChatWindow({ onClose, onMinimize, children, loading, error }) {
  return (
    <div className="fixed bottom-24 right-6 w-[380px] h-[600px] bg-white rounded-chat shadow-xl flex flex-col z-50 animate-fade-in">
      {/* Header */}
      <div className="h-16 bg-primary-blue flex items-center justify-between px-6 rounded-t-chat">
        <span className="text-white text-lg font-semibold">Support Assistant</span>
        <div className="flex gap-2">
          <button onClick={onMinimize} aria-label="Minimize" className="text-white hover:text-gray-200">
            <svg width="20" height="20" fill="none" viewBox="0 0 20 20"><rect y="9" width="20" height="2" rx="1" fill="currentColor"/></svg>
          </button>
          <button onClick={onClose} aria-label="Close" className="text-white hover:text-gray-200">
            <svg width="20" height="20" fill="none" viewBox="0 0 20 20"><path d="M6 6l8 8M6 14L14 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
          </button>
        </div>
      </div>
      {/* Body */}
      <div className="flex-1 overflow-y-auto bg-white p-4">{children}</div>
      {/* Footer: loading/error state */}
      <div className="p-4 border-t border-gray-100 bg-white">
        {loading && <div className="text-primary-blue text-xs mb-2">Generating AI reply...</div>}
        {error && <div className="text-red-500 text-xs mb-2">{error}</div>}
        <div className="text-xs text-gray-500 text-right mt-1">Powered by AI</div>
      </div>
    </div>
  );
}
