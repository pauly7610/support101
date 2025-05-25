import React, { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

interface WebSocketContextType {
  socket: WebSocket | null;
  status: "connecting" | "open" | "closed" | "error";
  send: (msg: any) => void;
  lastMessage: any;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

// Use Vite/CRA/webpack env variable or fallback
const WS_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_WS_URL) ||
               "ws://localhost:8000/ws";

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<"connecting" | "open" | "closed" | "error">("connecting");
  const [lastMessage, setLastMessage] = useState<any>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: number;
    let reconnectAttempts = 0;
    let intentionalClose = false;

    function connect() {
      ws = new window.WebSocket(WS_URL);
      socketRef.current = ws;
      setStatus("connecting");

      ws.onopen = () => {
        setStatus("open");
        reconnectAttempts = 0;
      };

      ws.onmessage = (event) => {
        setLastMessage(event.data);
      };

      ws.onerror = () => {
        setStatus("error");
        ws.close();
      };

      ws.onclose = () => {
        setStatus("closed");
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

  const send = (msg: any) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
  };

  return (
    <WebSocketContext.Provider value={{ socket: socketRef.current, status, send, lastMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error("useWebSocket must be used within a WebSocketProvider");
  return ctx;
};
