import { createRoot } from 'react-dom/client';
import { WebSocketProvider } from './components/WebSocketProvider.tsx';
import CopilotPanel from './components/agent/Copilot/index.js';

const root = document.createElement('div');
document.body.appendChild(root);
createRoot(root).render(
  <WebSocketProvider>
    <CopilotPanel />
  </WebSocketProvider>,
);
