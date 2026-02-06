import { useEffect, useRef, useState } from 'react';

import * as idb from 'idb-keyval';
import Sentiment from 'sentiment';
import { generateSuggestedReply, reportEscalation } from '../api';

interface ChatMessage {
  sender: string;
  text: string;
  timestamp: number;
  sentiment?: string;
  sources?: string[];
  error?: boolean;
  image?: string | ArrayBuffer | null;
  reaction?: string;
}

const CHAT_HISTORY_KEY = 'chat_history';
const ESCALATION_LOG_KEY = 'escalation_log';
const sentiment = new Sentiment(undefined);

function saveHistory(history: unknown[]) {
  idb.set(CHAT_HISTORY_KEY, history);
}
async function loadHistory() {
  return (await idb.get(CHAT_HISTORY_KEY)) || [];
}
async function saveEscalation(escalation: Record<string, unknown>) {
  idb.get(ESCALATION_LOG_KEY).then((log: unknown[] = []) => {
    idb.set(ESCALATION_LOG_KEY, [...log, escalation]);
  });
  // Backend analytics reporting (non-blocking)
  try {
    await reportEscalation(escalation);
  } catch (err) {
    // Do not block UI on analytics error
    // Optionally, log to Sentry or similar
    console.error('Failed to report escalation', err);
  }
}

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
  const result = sentiment.analyze(text, undefined, undefined);
  if (result.score < 0 || urgentWords.some((w) => text.toLowerCase().includes(w))) return 'urgent';
  return 'normal';
}

export default function ChatWidgetBackend() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [escalate, setEscalate] = useState(false);
  const [theme, setTheme] = useState('light');

  const [typing, setTyping] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [unread, setUnread] = useState(0);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadHistory().then(setMessages);
  }, []);
  useEffect(() => {
    saveHistory(messages);
  }, [messages]);
  useEffect(() => {
    if (chatEndRef.current) (chatEndRef.current as HTMLDivElement).scrollIntoView({ behavior: 'smooth' });
  }, [messages, minimized]);
  useEffect(() => {
    if (!minimized) setUnread(0);
  }, [minimized]);

  function handleInputKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    sendMessage();
  }

  async function sendMessage() {
    if (!input.trim()) return;
    const sentimentResult = analyzeSentiment(input);
    if (sentimentResult === 'urgent') {
      setEscalate(true);
      saveEscalation({ text: input, timestamp: Date.now() });
    }
    const newMsg = {
      sender: 'user',
      text: input,
      timestamp: Date.now(),
      sentiment: sentimentResult,
    };
    setMessages((prev) => [...prev, newMsg]);
    setInput('');
    setTyping(true);
    try {
      const ticketContext = { ticket_id: 'customer-chat', user_id: 'customer-1', content: input };
      const result = await generateSuggestedReply(ticketContext);
      setMessages((msgs) => [
        ...msgs,
        {
          sender: 'agent',
          text: result.reply_text,
          timestamp: Date.now(),
          sentiment: 'normal',
          sources: result.sources,
        },
      ]);
    } catch {
      setMessages((msgs) => [
        ...msgs,
        {
          sender: 'agent',
          text: 'Sorry, there was an error processing your request. [Retry]',
          timestamp: Date.now(),
          sentiment: 'normal',
        },
      ]);
    } finally {
      setTyping(false);
      if (minimized) setUnread((u) => u + 1);
    }
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

  function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const target = event.target;
    const file = target?.files ? target.files[0] : null;
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setMessages((msgs) => [
          ...msgs,
          {
            sender: 'user',
            text: '[Image]',
            image: ev.target?.result,
            timestamp: Date.now(),
            sentiment: 'normal',
          },
        ]);
      };
      reader.readAsDataURL(file);
    }
  }

  function handleReaction(idx: number) {
    setMessages((msgs) =>
      msgs.map((m, i) =>
        i === idx ? { ...m, reaction: m.reaction === 'like' ? undefined : 'like' } : m,
      ),
    );
  }

  return (
    <div
      className={`w-full max-w-md mx-auto border rounded shadow flex flex-col h-[500px] ${
        theme === 'dark' ? 'bg-gray-900 text-gray-100' : 'bg-white'
      }`}
      aria-label="Customer chat widget"
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
          <button
            onClick={() => setMinimized((m) => !m)}
            aria-label={minimized ? 'Open chat' : 'Minimize chat'}
            className="ml-2 rounded bg-gray-200 px-2 py-1 relative"
          >
            {minimized ? '💬' : '—'}
            {unread > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full px-1">
                {unread}
              </span>
            )}
          </button>
          {escalate && (
            <span className="ml-2 px-2 py-1 bg-red-600 text-xs rounded" aria-live="assertive">
              URGENT
            </span>
          )}
        </div>
      </header>
      {!minimized && (
        <>
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
                >
                  {msg.text}
                  {msg.image && (
                    <img
                      src={msg.image as string}
                      alt="uploaded"
                      className="mt-2 rounded max-w-[180px] max-h-[120px] border"
                    />
                  )}
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
                  <button
                    onClick={() => handleReaction(i)}
                    aria-label="Like message"
                    className="ml-2 text-xs focus:ring-2 focus:ring-blue-400"
                    style={{ background: 'none', border: 'none', cursor: 'pointer' }}
                  >
                    {msg.reaction === 'like' ? '👍' : '👍🏻'}
                  </button>
                  {msg.sources && (
                    <div className="text-xs mt-1 text-primary-blue-light">
                      Sources:{' '}
                      {msg.sources.map((s: string, idx: number) => (
                        <span key={idx}>
                          {s}
                          {idx < (msg.sources?.length ?? 0) - 1 ? ', ' : ''}
                        </span>
                      ))}
                    </div>
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
            {typing && (
              <div className="flex items-center gap-2 text-sm text-gray-500 animate-pulse mt-2">
                <span>🤖</span> <span>Agent is responding...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </main>
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
            <input
              type="file"
              accept="image/*"
              onChange={handleFileUpload}
              aria-label="Upload image"
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="bg-gray-200 px-2 py-2 rounded cursor-pointer focus:ring-2 focus:ring-blue-400"
              title="Upload image"
              aria-label="Upload image"
            >
              📎
            </label>
            <button
              type="submit"
              className="bg-primary-blue text-white px-4 py-2 rounded font-medium focus:ring-2 focus:ring-blue-400"
              disabled={!input.trim()}
              aria-label="Send message"
            >
              Send
            </button>
          </form>
        </>
      )}
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
  );
}
