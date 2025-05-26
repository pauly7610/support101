import React, { useState, useRef, useEffect } from 'react';
import FloatingChatButton from './FloatingChatButton';
import ChatWindow from './ChatWindow';
import MessageBubble from './MessageBubble';

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [messages, setMessages] = useState([
    {
      from: 'bot',
      text: 'Hi! How can I help you today?',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [input, setInput] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (open && !minimized && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open, minimized]);

  // eslint-disable-next-line @typescript-eslint/no-var-requires

  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { generateSuggestedReply } = require('../../api');

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    const now = new Date().toLocaleTimeString();
    setMessages([...messages, { from: 'user', text: input, timestamp: now }]);
    // setLoading(true);
    // setError(null);
    try {
      // Compose TicketContext object
      const ticketContext = {
        ticket_id: 'customer-chat',
        user_id: 'customer-1',
        content: input,
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
      // setError('Sorry, something went wrong.');
    } finally {
      // setLoading(false);
      setInput('');
    }
  };

  if (!open) {
    return <FloatingChatButton onClick={() => setOpen(true)} />;
  }

  if (minimized) {
    return (
      <button
        className="fixed bottom-6 right-6 w-12 h-12 rounded-full bg-primary-blue text-white flex items-center justify-center shadow-chat-float z-50"
        onClick={() => setMinimized(false)}
        aria-label="Restore chat"
      >
        <svg width="24" height="24" fill="none" viewBox="0 0 24 24">
          <rect y="9" width="24" height="6" rx="3" fill="currentColor" />
        </svg>
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
    >
      <div className="flex flex-col gap-2 pb-4" style={{ minHeight: 360 }}>
        {messages.map((msg, i) => (
          <MessageBubble key={i} {...msg} />
        ))}
      </div>
      {/* Footer input override */}
      <form
        className="flex items-center gap-2 mt-auto"
        onSubmit={handleSend}
        style={{ marginBottom: 0 }}
      >
        <input
          ref={inputRef}
          className="flex-1 rounded-full border border-gray-200 px-4 py-2 text-base focus:outline-none focus:ring-2 focus:ring-primary-blue"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button
          type="submit"
          className="bg-primary-blue hover:bg-primary-blue-dark text-white rounded-full px-5 py-2 font-medium transition-colors"
        >
          Send
        </button>
      </form>
      <div className="text-xs text-gray-500 text-right mt-1">Powered by AI</div>
    </ChatWindow>
  );
}
