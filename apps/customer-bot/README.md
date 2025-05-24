# Customer Bot (Next.js Widget)

A Next.js + Tailwind CSS chatbot widget for customer-facing support.

## Features
- Floating chat button and window for customer interaction
- Sends customer questions to backend for RAG-based AI replies
- Displays reply and sources in chat bubbles
- Uses shared design system and UI primitives

## Integration
- Consumes `/generate_reply` endpoint from the backend
- Configure `NEXT_PUBLIC_BACKEND_URL` in `.env` for deployment

## Dev
- `npm install`
- `npm run dev` (with backend running)
