import React from 'react';
import { createRoot } from 'react-dom/client';
import CopilotPanel from './components/agent/Copilot';
import { WebSocketProvider } from './components/WebSocketProvider';

const root = document.createElement('div');
document.body.appendChild(root);
createRoot(root).render(
  <WebSocketProvider>
    <CopilotPanel />
  </WebSocketProvider>,
);
