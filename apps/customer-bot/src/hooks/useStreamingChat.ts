/**
 * Streaming chat hook built on Vercel AI SDK's useChat.
 *
 * Provides:
 * - Streaming responses from /api/chat
 * - Automatic message history
 * - Loading/error states
 * - Sentiment analysis on user messages
 * - Source citation extraction
 *
 * Falls back gracefully when the AI SDK is not available
 * (e.g., during SSR or when dependencies are missing).
 */

import { useCallback, useRef, useState } from 'react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt?: Date;
  sources?: Array<{
    url: string;
    excerpt: string;
    confidence: number;
    last_updated?: string;
  }>;
  sentiment?: 'urgent' | 'normal';
}

interface UseStreamingChatOptions {
  api?: string;
  onError?: (error: Error) => void;
  onFinish?: (message: ChatMessage) => void;
}

interface UseStreamingChatReturn {
  messages: ChatMessage[];
  input: string;
  setInput: (input: string) => void;
  handleSubmit: (e?: React.FormEvent) => Promise<void>;
  isLoading: boolean;
  error: Error | null;
  reload: () => Promise<void>;
  stop: () => void;
  append: (message: Omit<ChatMessage, 'id' | 'createdAt'>) => Promise<void>;
  setMessages: (messages: ChatMessage[]) => void;
}

const URGENT_WORDS = ['urgent', 'immediately', 'asap', 'help', 'problem', 'angry', 'cancel', 'refund'];

function analyzeSentiment(text: string): 'urgent' | 'normal' {
  const lower = text.toLowerCase();
  if (URGENT_WORDS.some((w) => lower.includes(w))) return 'urgent';
  return 'normal';
}

export function useStreamingChat(options: UseStreamingChatOptions = {}): UseStreamingChatReturn {
  const { api = '/api/chat', onError, onFinish } = options;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const append = useCallback(
    async (message: Omit<ChatMessage, 'id' | 'createdAt'>) => {
      const userMsg: ChatMessage = {
        ...message,
        id: `msg-${Date.now()}-user`,
        createdAt: new Date(),
        sentiment: message.role === 'user' ? analyzeSentiment(message.content) : undefined,
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const allMessages = [...messages, userMsg].map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const res = await fetch(api, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: allMessages }),
          signal: controller.signal,
        });

        if (!res.ok) {
          throw new Error(`Chat API returned ${res.status}`);
        }

        const contentType = res.headers.get('Content-Type') || '';

        if (contentType.includes('text/plain') || contentType.includes('text/event-stream')) {
          // Streaming response — read chunks
          const reader = res.body?.getReader();
          if (!reader) throw new Error('No response body');

          const assistantMsg: ChatMessage = {
            id: `msg-${Date.now()}-assistant`,
            role: 'assistant',
            content: '',
            createdAt: new Date(),
          };

          setMessages((prev) => [...prev, assistantMsg]);

          const decoder = new TextDecoder();
          let fullText = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            // Parse AI SDK data stream format: lines starting with "0:" contain text
            const lines = chunk.split('\n');
            for (const line of lines) {
              if (line.startsWith('0:')) {
                try {
                  const text = JSON.parse(line.slice(2));
                  fullText += text;
                  setMessages((prev) =>
                    prev.map((m) => (m.id === assistantMsg.id ? { ...m, content: fullText } : m))
                  );
                } catch {
                  // Not JSON, append raw
                  fullText += line.slice(2);
                  setMessages((prev) =>
                    prev.map((m) => (m.id === assistantMsg.id ? { ...m, content: fullText } : m))
                  );
                }
              }
            }
          }

          const finalMsg = { ...assistantMsg, content: fullText };
          onFinish?.(finalMsg);
        } else {
          // JSON response (non-streaming fallback)
          const data = await res.json();
          const assistantMsg: ChatMessage = {
            id: data.id || `msg-${Date.now()}-assistant`,
            role: 'assistant',
            content: data.content || data.reply_text || 'Sorry, no response.',
            createdAt: new Date(),
            sources: data.sources,
          };
          setMessages((prev) => [...prev, assistantMsg]);
          onFinish?.(assistantMsg);
        }
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        onError?.(error);
      } finally {
        setIsLoading(false);
        abortRef.current = null;
      }
    },
    [api, messages, onError, onFinish]
  );

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!input.trim()) return;
      const text = input;
      setInput('');
      await append({ role: 'user', content: text });
    },
    [input, append]
  );

  const reload = useCallback(async () => {
    if (messages.length < 2) return;
    // Remove last assistant message and re-send
    const lastUserIdx = messages.map((m) => m.role).lastIndexOf('user');
    if (lastUserIdx === -1) return;
    const lastUserMsg = messages[lastUserIdx];
    setMessages((prev) => prev.slice(0, lastUserIdx));
    await append({ role: 'user', content: lastUserMsg.content });
  }, [messages, append]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
  }, []);

  return {
    messages,
    input,
    setInput,
    handleSubmit,
    isLoading,
    error,
    reload,
    stop,
    append,
    setMessages,
  };
}
