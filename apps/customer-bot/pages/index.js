import { useState } from 'react';

export default function Chatbot() {
  const [messages, setMessages] = useState([
    { from: 'bot', text: 'Hi! How can I help you today?' }
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
      body: JSON.stringify({ ticket_id: 'demo', user_id: 'customer', content: input })
    });
    const data = await res.json();
    setMessages(msgs => [...msgs, { from: 'bot', text: data.reply, sources: data.sources }]);
    setInput('');
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg p-6">
        <div className="mb-4 h-80 overflow-y-auto flex flex-col gap-2">
          {messages.map((msg, i) => (
            <div key={i} className={msg.from === 'bot' ? 'text-left' : 'text-right'}>
              <div className={msg.from === 'bot' ? 'bg-blue-100 text-blue-900' : 'bg-gray-200 text-gray-900'} + " inline-block px-3 py-2 rounded-lg max-w-xs">
                {msg.text}
                {msg.sources && (
                  <div className="text-xs mt-1 text-blue-600">
                    Sources: {msg.sources.map((s, idx) => <span key={idx}>{s}{idx < msg.sources.length-1 ? ', ' : ''}</span>)}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        <form onSubmit={sendMessage} className="flex gap-2">
          <input
            className="flex-1 border rounded px-3 py-2"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={loading}
          />
          <button type="submit" className="bg-blue-500 text-white px-4 py-2 rounded" disabled={loading}>
            {loading ? '...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
}
