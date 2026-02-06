import React from 'react';
import { X, Minus, Bot, Sparkles } from 'lucide-react';
import { cn } from '../../../lib/utils';

import PropTypes from 'prop-types';

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 px-4 py-2 animate-fade-in">
      <div className={cn(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        'bg-gradient-to-br from-brand-100 to-brand-200 text-brand-600',
        'dark:from-brand-800 dark:to-brand-900 dark:text-brand-300',
      )}>
        <Bot className="w-4 h-4" />
      </div>
      <div className="flex gap-1 px-4 py-3 bg-gray-100 dark:bg-slate-800 rounded-2xl rounded-tl-md">
        <span className="w-2 h-2 bg-gray-400 dark:bg-slate-500 rounded-full animate-bounce-dot" />
        <span className="w-2 h-2 bg-gray-400 dark:bg-slate-500 rounded-full animate-bounce-dot [animation-delay:0.2s]" />
        <span className="w-2 h-2 bg-gray-400 dark:bg-slate-500 rounded-full animate-bounce-dot [animation-delay:0.4s]" />
      </div>
    </div>
  );
}

export default function ChatWindow({ onClose, onMinimize, children, loading, error }) {
  return (
    <div className={cn(
      'fixed bottom-24 right-6 z-50',
      'w-[380px] h-[600px]',
      'bg-white dark:bg-slate-900',
      'rounded-2xl shadow-chat-window',
      'flex flex-col overflow-hidden',
      'animate-scale-in',
      'border border-gray-200/50 dark:border-slate-700/50',
    )}>
      {/* Header */}
      <div className="glass-header px-5 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="text-white text-sm font-semibold leading-tight">Support Assistant</h2>
            <p className="text-white/70 text-[10px]">Powered by AI</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onMinimize}
            aria-label="Minimize"
            className={cn(
              'w-7 h-7 rounded-lg flex items-center justify-center',
              'text-white/80 hover:text-white hover:bg-white/10',
              'transition-colors focus:outline-none focus:ring-2 focus:ring-white/30',
            )}
          >
            <Minus className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            aria-label="Close"
            className={cn(
              'w-7 h-7 rounded-lg flex items-center justify-center',
              'text-white/80 hover:text-white hover:bg-white/10',
              'transition-colors focus:outline-none focus:ring-2 focus:ring-white/30',
            )}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin bg-white dark:bg-slate-900">
        {children}
        {loading && <TypingIndicator />}
      </div>
      {/* Footer: error state */}
      {error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-t border-red-100 dark:border-red-900/30">
          <p className="text-red-600 dark:text-red-400 text-xs">{error}</p>
        </div>
      )}
    </div>
  );
}

ChatWindow.propTypes = {
  onClose: PropTypes.func.isRequired,
  onMinimize: PropTypes.func.isRequired,
  children: PropTypes.node,
  loading: PropTypes.bool,
  error: PropTypes.string,
};
