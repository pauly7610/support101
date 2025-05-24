import React, { useEffect, useState } from 'react';

export default function Sidebar() {
  const [suggested, setSuggested] = useState('Loading...');

  useEffect(() => {
    // Dummy fetch to backend
    fetch('http://localhost:8000/generate_reply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticket_id: '1', user_id: 'agent1', content: 'Hello, I need help.' })
    })
      .then(res => res.json())
      .then(data => setSuggested(data.reply || 'No suggestion'));
  }, []);

  return (
    <div style={{ padding: 16 }}>
      <h2>Agent Copilot</h2>
      <div style={{ margin: '16px 0', background: '#fff', padding: 12, borderRadius: 6, boxShadow: '0 1px 2px rgba(0,0,0,0.03)' }}>
        <strong>Suggested Reply:</strong>
        <div>{suggested}</div>
      </div>
      <small>Injected into Zendesk/Intercom</small>
    </div>
  );
}
