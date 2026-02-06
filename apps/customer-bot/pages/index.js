import { useState } from 'react';

export default function Chatbot() {
  const [messages, setMessages] = useState([
    { from: 'bot', text: 'Hi! How can I help you today?' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    setMessages([...messages, { from: 'user', text: input }]);
    setLoading(true);
    const res = await fetch('http://localhost:8000/generate_reply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticket_id: 'demo', user_id: 'customer', content: input }),
    });
    const data = await res.json();
    setMessages((msgs) => [...msgs, { from: 'bot', text: data.reply, sources: data.sources }]);
    setInput('');
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-6 flex flex-col justify-between min-h-[32rem]">
        <div className="text-lg font-semibold text-gray-800 mb-2">Support Chat</div>
        <div className="mb-4 h-80 overflow-y-auto flex flex-col gap-2">
          {messages.map((msg, i) => (
            <div
              key={`${msg.from}-${msg.text.slice(0, 20)}-${i}`}
              className={msg.from === 'bot' ? 'text-left' : 'text-right'}
            >
              <div
                className={`${
                  msg.from === 'bot' ? 'bg-blue-100 text-blue-900' : 'bg-gray-200 text-gray-900'
                } inline-block px-3 py-2 rounded-lg max-w-xs`}
              >
                {msg.text}
                {msg.sources && (
                  <div className="text-xs mt-1 text-blue-600">
                    Sources:{' '}
                    {msg.sources.map((s, idx) => (
                      <span key={s}>
                        {s}
                        {idx < msg.sources.length - 1 ? ', ' : ''}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        <form onSubmit={sendMessage} className="flex gap-2 items-center mt-4">
          <input
            className="flex-1 rounded-full px-4 py-2 border border-gray-300 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition placeholder-gray-400 text-base bg-white hover:shadow focus:shadow-lg"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything…"
            aria-label="Message input"
            disabled={loading}
          />
          <button
            type="submit"
            className="ml-2 px-4 py-2 rounded-full bg-blue-500 hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 text-white font-semibold shadow transition disabled:opacity-60 flex items-center justify-center"
            aria-label="Send message"
            disabled={loading || !input.trim()}
          >
            {loading ? (
              <svg
                className="animate-spin h-5 w-5 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-label="Loading"
              >
                <title>Loading</title>
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
            ) : (
              'Send'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
