import React, { useState } from 'react';
import { generateSuggestedReply } from '../../api';

export default function CopilotSidebar() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [suggested, setSuggested] = useState(null);

  // Example static context, in real app pull from selected ticket/user
  const ticketContext = {
    ticket_id: 'demo-ticket-1',
    user_id: 'demo-user-1',
    content: input,
    // add other context fields as needed
  };

  const handleSuggest = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuggested(null);
    try {
      const result = await generateSuggestedReply(ticketContext);
      setSuggested(result);
    } catch (err) {
      setError('Failed to fetch suggestion.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <aside className="fixed top-0 right-0 w-[360px] h-full bg-white border-l border-gray-200 shadow-lg flex flex-col z-40">
      <header className="h-16 flex items-center px-6 border-b border-gray-100 bg-primary-blue">
        <span className="text-white text-lg font-semibold">AI Copilot</span>
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
          <div className="mb-6">
            <div className="font-semibold text-base mb-2">Suggested Reply</div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 flex flex-col gap-1">
              <span className="text-sm">{suggested.reply_text}</span>
            </div>
            {suggested.sources && suggested.sources.length > 0 && (
              <div className="mt-2">
                <div className="font-semibold text-xs mb-1">Sources:</div>
                <ul className="list-disc ml-5 text-xs">
                  {suggested.sources.map((src, idx) => (
                    <li key={idx}>
                      <a href={src.url} target="_blank" rel="noopener noreferrer" className="text-primary-blue underline">{src.title || src.url}</a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
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
