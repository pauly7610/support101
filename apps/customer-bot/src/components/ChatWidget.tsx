import React, { useState, useEffect, useRef } from 'react';
// Remove problematic type imports, use 'any' as fallback for event handlers if needed.

// Simple IndexedDB wrapper using idb-keyval
import Sentiment from 'sentiment';
import * as idb from 'idb-keyval';

const CHAT_HISTORY_KEY = 'chat_history';
const sentiment = new Sentiment();

type ChatMessage = {
  sender: string;
  text: string;
  timestamp: number;
  sentiment: string;
  error?: boolean;
};

function saveHistory(history: ChatMessage[]) {
  idb.set(CHAT_HISTORY_KEY, history);
}
async function loadHistory(): Promise<ChatMessage[]> {
  return (await idb.get(CHAT_HISTORY_KEY)) || [];
}

// Real ML sentiment analysis
function analyzeSentiment(text: string): 'urgent' | 'normal' {
  const urgentWords = [
    'urgent',
    'immediately',
    'asap',
    'help',
    'problem',
    'angry',
    'cancel',
    'refund',
  ];
  const result = sentiment.analyze(text);
  if (result.score < 0 || urgentWords.some((w) => text.toLowerCase().includes(w))) return 'urgent';
  return 'normal';
}

export default function ChatWidget() {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [feedbackSent, setFeedbackSent] = useState(false);

  async function handleFeedbackSubmit(event: Event) {
    event.preventDefault();
    await fetch('/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback }),
    });
    setFeedbackSent(true);
    setTimeout(() => {
      setShowFeedback(false);
      setFeedbackSent(false);
      setFeedback('');
    }, 2000);
  }

  const [messages, setMessages] = useState([]); // Remove type argument
  const [input, setInput] = useState(''); // Remove type argument
  const [escalate, setEscalate] = useState(false); // Remove type argument
  const [theme, setTheme] = useState('light'); // Remove type argument

  const chatEndRef = useRef(null); // Remove type argument

  // Load chat history from IndexedDB
  useEffect(() => {
    loadHistory().then(setMessages);
  }, []);

  // Persist chat history
  useEffect(() => {
    saveHistory(messages);
  }, [messages]);

  // Scroll to bottom on new message
  useEffect(() => {
    if (chatEndRef.current)
      (chatEndRef.current as HTMLDivElement).scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Keyboard accessibility for input: Enter to send, Shift+Enter for newline
  function handleInputKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e); // Remove cast
    }
  }

  function handleSend(e: Event) {
    e.preventDefault();
    if (!input.trim()) return;
    const sentimentResult = analyzeSentiment(input);
    if (sentimentResult === 'urgent') setEscalate(true);
    const newMsg = {
      sender: 'user',
      text: input,
      timestamp: Date.now(),
      sentiment: sentimentResult,
    };
    setMessages((prev) => [...prev, newMsg]);
    setInput('');
    setTimeout(() => {
      // 10% chance of agent error for demo
      if (Math.random() < 0.1) {
        setMessages((msgs) => [
          ...msgs,
          {
            sender: 'agent',
            text: 'Sorry, there was an error processing your request. [Retry]',
            timestamp: Date.now() + 1000,
            sentiment: 'normal',
            error: true,
          },
        ]);
      } else {
        const agentReply = {
          sender: 'agent',
          // eslint-disable-next-line operator-linebreak
          text: `Thank you for your message${
            sentimentResult === 'urgent' ? ', we are escalating this to support.' : '!'
          }`,

          timestamp: Date.now() + 1000,
          sentiment: 'normal',
        };
        setMessages((msgs) => [...msgs, agentReply]);
      }
    }, 700);
  }

  function handleRetry(idx: number) {
    setMessages((msgs) => msgs.filter((_, i) => i !== idx));
    setTimeout(() => {
      setMessages((msgs) => [
        ...msgs,
        {
          sender: 'agent',
          text: 'Thank you for your message! (Retried)',
          timestamp: Date.now(),
          sentiment: 'normal',
        },
      ]);
    }, 700);
  }

  function handleClear() {
    setMessages([]);
    setEscalate(false);
  }

  function toggleTheme() {
    setTheme((t) => (t === 'light' ? 'dark' : 'light'));
  }

  return (
    <>
      <div
        className={`w-full max-w-md mx-auto border rounded shadow flex flex-col h-[500px] ${
          theme === 'dark' ? 'bg-gray-900 text-gray-100' : 'bg-white'
        }`}
        aria-label="Customer chat widget"
        tabIndex={0}
        style={{ outline: escalate ? '2px solid #ff4d4f' : undefined }}
      >
        <header
          className={`px-4 py-3 rounded-t flex items-center justify-between ${
            theme === 'dark' ? 'bg-gray-800 text-gray-100' : 'bg-primary-blue text-white'
          }`}
        >
          <span className="font-semibold">Customer Chat</span>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              aria-label="Toggle light/dark theme"
              className="rounded focus:ring-2 focus:ring-blue-400 px-2 py-1"
              style={{
                background: theme === 'dark' ? '#222' : '#e6f0ff',
                color: theme === 'dark' ? '#fff' : '#222',
                border: 'none',
              }}
            >
              {theme === 'dark' ? '🌙' : '☀️'}
            </button>
            <button
              onClick={handleClear}
              aria-label="Clear chat history"
              className="rounded focus:ring-2 focus:ring-blue-400 px-2 py-1 ml-1"
              style={{ background: '#ff4d4f', color: '#fff', border: 'none' }}
            >
              Clear
            </button>
            {escalate && (
              <span className="ml-2 px-2 py-1 bg-red-600 text-xs rounded" aria-live="assertive">
                URGENT
              </span>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-2" aria-live="polite">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`mb-2 flex items-end gap-2 ${
                msg.sender === 'user' ? 'justify-end' : 'justify-start'
              } animate-fadein-slideup`}
              aria-label={msg.sender === 'user' ? 'You' : 'Agent'}
              style={{ animation: 'fadein-slideup 0.4s' }}
            >
              {msg.sender === 'agent' && (
                <span
                  aria-hidden
                  className="rounded-full bg-blue-200"
                  style={{
                    width: 28,
                    height: 28,
                    display: 'inline-block',
                    background: '#dbeafe',
                    textAlign: 'center',
                    fontWeight: 700,
                    fontSize: 18,
                    lineHeight: '28px',
                    color: '#1e40af',
                  }}
                >
                  🤖
                </span>
              )}
              <span
                className={`inline-block px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 ${
                  msg.sender === 'user'
                    ? theme === 'dark'
                      ? 'bg-blue-900 text-blue-100'
                      : 'bg-blue-100 text-blue-900'
                    : theme === 'dark'
                    ? 'bg-gray-800 text-gray-100'
                    : 'bg-gray-100 text-gray-800'
                }`}
                style={{
                  color: theme === 'dark' ? '#fff' : '#1a1a1a',
                  background:
                    msg.sender === 'user'
                      ? theme === 'dark'
                        ? '#1e40af'
                        : '#e6f0ff'
                      : theme === 'dark'
                      ? '#222'
                      : '#f4f4f4',
                  minWidth: 40,
                  maxWidth: 240,
                  wordBreak: 'break-word',
                  border: msg.sentiment === 'urgent' ? '2px solid #ff4d4f' : undefined,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                }}
                tabIndex={0}
              >
                {msg.text}
                <div
                  className="text-xs text-gray-400 mt-1"
                  aria-label="Timestamp"
                  style={{ color: theme === 'dark' ? '#e0e7ef' : '#888' }}
                >
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
                {msg.error && (
                  <button
                    onClick={() => handleRetry(i)}
                    aria-label="Retry message"
                    className="ml-2 text-xs underline text-blue-600 focus:ring-2 focus:ring-blue-400"
                    style={{ background: 'none', border: 'none', cursor: 'pointer' }}
                  >
                    Retry
                  </button>
                )}
              </span>
              {msg.sender === 'user' && (
                <span
                  aria-hidden
                  className="rounded-full bg-blue-600"
                  style={{
                    width: 28,
                    height: 28,
                    display: 'inline-block',
                    background: '#2563eb',
                    textAlign: 'center',
                    fontWeight: 700,
                    fontSize: 18,
                    lineHeight: '28px',
                    color: '#fff',
                  }}
                >
                  🧑
                </span>
              )}
            </div>
          ))}
          <div ref={chatEndRef} />
        </main>
        {/* Chat Input */}
        <form className="p-3 flex gap-2 border-t" onSubmit={handleSend}>
          <label htmlFor="chat-input" className="sr-only">
            Type your message
          </label>
          <textarea
            id="chat-input"
            className="flex-1 border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            aria-label="Chat input"
            style={{
              color: theme === 'dark' ? '#fff' : '#1a1a1a',
              background: theme === 'dark' ? '#222' : '#fff',
              borderColor: '#ccc',
              minHeight: 36,
              maxHeight: 90,
              resize: 'vertical',
            }}
            onKeyDown={handleInputKeyDown}
          />
          <button
            type="submit"
            className="bg-primary-blue text-white px-4 py-2 rounded font-medium focus:ring-2 focus:ring-blue-400"
            disabled={!input.trim()}
            aria-label="Send message"
          >
            Send
          </button>
        </form>
        {/* Animations and dark theme tweaks */}
        <style>{`
          @keyframes fadein-slideup {
            0% { opacity: 0; transform: translateY(24px); }
            100% { opacity: 1; transform: translateY(0); }
          }
          .animate-fadein-slideup { animation: fadein-slideup 0.4s; }
          .bg-primary-blue { background: #2563eb !important; }
          .focus-visible:focus { outline: 2px solid #2563eb; }
        `}</style>
      </div>
      {/* Floating Feedback Button */}
      <button
        className="fixed bottom-8 left-8 z-50 bg-blue-600 text-white px-4 py-2 rounded-full shadow-lg hover:bg-blue-700 focus:outline-none focus:ring"
        aria-label="Send Feedback"
        onClick={() => setShowFeedback(true)}
      >
        Send Feedback
      </button>
      {/* Feedback Modal */}
      {showFeedback && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-2">Send Feedback</h3>
            {feedbackSent ? (
              <div className="text-green-600">Thank you for your feedback!</div>
            ) : (
              <form onSubmit={handleFeedbackSubmit}>
                <textarea
                  className="w-full border rounded p-2 mb-3 dark:bg-gray-800 dark:text-white"
                  rows={4}
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Your feedback or issue..."
                  aria-label="Feedback textarea"
                  required
                />
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    className="px-4 py-2 rounded bg-gray-300 dark:bg-gray-700 hover:bg-gray-400 dark:hover:bg-gray-600"
                    onClick={() => setShowFeedback(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700"
                  >
                    Submit
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
