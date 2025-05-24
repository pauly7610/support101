import React from 'react';
import { createRoot } from 'react-dom/client';
import CopilotPanel from './components/agent/Copilot';

const root = document.createElement('div');
document.body.appendChild(root);
createRoot(root).render(<CopilotPanel />);
