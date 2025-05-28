import React from 'react';
import { createRoot } from 'react-dom/client';
import CopilotPanel from './components/agent/Copilot/index.js';
import { WebSocketProvider } from './components/WebSocketProvider.tsx';

const root = document.createElement('div');
document.body.appendChild(root);
createRoot(root).render(
  <WebSocketProvider>
    <CopilotPanel />
  </WebSocketProvider>,
);
