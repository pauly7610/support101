import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageCircle } from 'lucide-react';
import { cn } from '../../../lib/utils';
import FloatingChatButton from './FloatingChatButton';
import ChatWindow from './ChatWindow';
import MessageBubble from './MessageBubble';

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [messages, setMessages] = useState([
    {
      from: 'bot',
      text: 'Hi! How can I help you today?',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [input, setInput] = useState('');
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (open && !minimized && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open, minimized]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { generateSuggestedReply } = require('../../api');

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const now = new Date().toLocaleTimeString();
    setMessages((prev) => [...prev, { from: 'user', text: input, timestamp: now }]);
    setLoading(true);
    setError(null);
    const currentInput = input;
    setInput('');
    try {
      const ticketContext = {
        ticket_id: 'customer-chat',
        user_id: 'customer-1',
        content: currentInput,
      };
      const result = await generateSuggestedReply(ticketContext);
      setMessages((msgs) => [
        ...msgs,
        {
          from: 'bot',
          text: result.reply_text,
          timestamp: new Date().toLocaleTimeString(),
          sources: result.sources?.map((src) => src.title || src.url),
        },
      ]);
    } catch (err) {
      setError('Sorry, something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return <FloatingChatButton onClick={() => setOpen(true)} />;
  }

  if (minimized) {
    return (
      <button
        className={cn(
          'fixed bottom-6 right-6 z-50',
          'w-12 h-12 rounded-full',
          'bg-gradient-to-br from-brand-500 to-brand-700',
          'text-white shadow-chat-float',
          'flex items-center justify-center',
          'hover:scale-105 active:scale-95',
          'transition-all duration-200',
          'focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2',
          'dark:from-brand-400 dark:to-brand-600',
        )}
        onClick={() => setMinimized(false)}
        aria-label="Restore chat"
      >
        <MessageCircle className="w-5 h-5" />
      </button>
    );
  }

  return (
    <ChatWindow
      onClose={() => {
        setOpen(false);
        setMinimized(false);
      }}
      onMinimize={() => setMinimized(true)}
      loading={loading}
      error={error}
    >
      <div className="flex flex-col pb-4 min-h-[360px]">
        {messages.map((msg, i) => (
          <MessageBubble key={i} {...msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      {/* Input area */}
      <form
        className="sticky bottom-0 flex items-center gap-2 p-3 bg-white dark:bg-slate-900 border-t border-gray-100 dark:border-slate-800"
        onSubmit={handleSend}
      >
        <input
          ref={inputRef}
          className={cn(
            'flex-1 rounded-full px-4 py-2.5 text-sm',
            'bg-gray-50 dark:bg-slate-800',
            'border border-gray-200 dark:border-slate-700',
            'text-gray-900 dark:text-slate-100',
            'placeholder:text-gray-400 dark:placeholder:text-slate-500',
            'focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500',
            'transition-all duration-200',
          )}
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className={cn(
            'w-10 h-10 rounded-full flex items-center justify-center',
            'bg-brand-500 text-white',
            'hover:bg-brand-600 active:scale-95',
            'disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-brand-500',
            'transition-all duration-200',
            'focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2',
            'dark:focus:ring-offset-slate-900',
          )}
          aria-label="Send message"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </ChatWindow>
  );
}
