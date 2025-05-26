import React, { useContext, useEffect, useRef, useState } from 'react';

interface WebSocketContextType {
  socket: WebSocket | null;
  status: 'connecting' | 'open' | 'closed' | 'error';
  send: (msg: string | object) => void;
  lastMessage: string | object | null;
}

const WebSocketContext = React.createContext<WebSocketContextType | undefined>(undefined); // TypeScript is correct here, but if this triggers an error, try without type argument:
// const WebSocketContext = React.createContext(undefined);

// Use Vite/CRA/webpack env variable or fallback
const WS_URL =
  (typeof globalThis !== 'undefined' && globalThis.process?.env?.VITE_WS_URL) ||
  (typeof import.meta !== 'undefined' &&
    (import.meta as { env?: Record<string, string> }).env?.VITE_WS_URL) ||
  'ws://localhost:8000/ws';

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  // Make sure ReactNode is accessible, import if needed
  const [status, setStatus] = useState<'connecting' | 'open' | 'closed' | 'error'>('connecting');
  const [lastMessage, setLastMessage] = useState<string | object | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: ReturnType<typeof setTimeout>;
    let reconnectAttempts = 0;
    let intentionalClose = false;

    function connect() {
      ws = new window.WebSocket(WS_URL);
      socketRef.current = ws;
      setStatus('connecting');

      ws.onopen = () => {
        setStatus('open');
        reconnectAttempts = 0;
      };

      ws.onmessage = (event) => {
        setLastMessage(event.data);
      };

      ws.onerror = () => {
        setStatus('error');
        ws.close();
      };

      ws.onclose = () => {
        setStatus('closed');
        if (!intentionalClose) {
          reconnectAttempts += 1;
          const timeout = Math.min(1000 * 2 ** reconnectAttempts, 30000);
          reconnectTimeout = setTimeout(connect, timeout);
        }
      };
    }

    connect();
    return () => {
      intentionalClose = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  const send: (msg: string | object) => void = (msg) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  };

  return (
    <WebSocketContext.Provider value={{ socket: socketRef.current, status, send, lastMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export const useWebSocket = (): WebSocketContextType => {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error('useWebSocket must be used within a WebSocketProvider');
  return ctx;
};
