import React from 'react';
import { createRoot } from 'react-dom/client';
import ChatWidgetBackend from './components/ChatWidgetBackend';

const root = document.createElement('div');
document.body.appendChild(root);
createRoot(root).render(<ChatWidgetBackend />);
