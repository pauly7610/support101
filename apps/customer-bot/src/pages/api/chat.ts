/**
 * Next.js API route for streaming chat via Vercel AI SDK.
 *
 * Proxies to the backend RAG endpoint with streaming support.
 * Falls back to the backend /generate_reply endpoint when
 * the AI SDK provider is not configured.
 */

import type { NextApiRequest, NextApiResponse } from 'next';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { messages } = req.body;
  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    return res.status(400).json({ error: 'messages array is required' });
  }

  const lastMessage = messages[messages.length - 1];
  const userQuery = lastMessage?.content || '';

  try {
    // Try streaming via AI SDK if OPENAI_API_KEY is set
    if (process.env.OPENAI_API_KEY) {
      const { openai } = await import('@ai-sdk/openai');
      const { streamText } = await import('ai');

      const result = streamText({
        model: openai(process.env.LLM_MODEL_NAME || 'gpt-4o'),
        system:
          'You are a helpful customer support assistant. Answer questions clearly and concisely. ' +
          'If you are unsure, say so. Be friendly and professional.',
        messages: messages.map((m: { role: string; content: string }) => ({
          role: m.role as 'user' | 'assistant' | 'system',
          content: m.content,
        })),
      });

      // Stream the response using AI SDK's toDataStreamResponse
      const response = result.toDataStreamResponse();

      // Forward headers
      res.setHeader('Content-Type', response.headers.get('Content-Type') || 'text/plain');
      res.setHeader('Cache-Control', 'no-cache');

      // Pipe the body
      const reader = response.body?.getReader();
      if (!reader) {
        return res.status(500).json({ error: 'Failed to create stream' });
      }

      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        res.write(decoder.decode(value, { stream: true }));
      }
      return res.end();
    }

    // Fallback: proxy to backend /generate_reply (non-streaming)
    const backendRes = await fetch(`${BACKEND_URL}/generate_reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ticket_id: 'customer-chat',
        user_id: 'customer-1',
        content: userQuery,
        user_query: userQuery,
      }),
    });

    if (!backendRes.ok) {
      const errBody = await backendRes.text();
      return res.status(backendRes.status).json({ error: errBody });
    }

    const data = await backendRes.json();

    // Format as AI SDK-compatible response for useChat
    // When not streaming, return a simple JSON response that useChat can parse
    return res.status(200).json({
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: data.reply_text || data.reply || 'Sorry, I could not generate a response.',
      sources: data.sources || [],
    });
  } catch (err) {
    console.error('Chat API error:', err);
    return res.status(500).json({
      error_type: 'chat_api_error',
      message: err instanceof Error ? err.message : 'Unknown error',
      retryable: true,
      documentation: 'https://api.support101/errors#E500',
    });
  }
}
