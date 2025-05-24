import React from 'react';

export default function MessageBubble({ from, text, timestamp, sources }) {
  const isUser = from === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-2`}>
      <div
        className={
          'max-w-[80%] px-4 py-3 rounded-bubble ' +
          (isUser
            ? 'bg-primary-blue text-white rounded-br-none'
            : 'bg-gray-100 text-gray-900 rounded-bl-none')
        }
      >
        <div>{text}</div>
        {sources && (
          <div className="text-xs mt-1 text-primary-blue-light">
            Sources: {sources.map((s, idx) => <span key={idx}>{s}{idx < sources.length-1 ? ', ' : ''}</span>)}
          </div>
        )}
        <div className="text-xs text-gray-500 mt-1 text-right">{timestamp}</div>
      </div>
    </div>
  );
}
