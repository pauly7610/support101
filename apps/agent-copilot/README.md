# Agent Copilot (Chrome Extension)

A React-based Chrome extension providing an AI-powered copilot sidebar for support agents.

## Features
- Interactive sidebar UI with sentiment, suggested responses, customer context, and knowledge base search
- Real-time websocket connection to backend
- Context-aware help and citation popup display
- Escalation analytics integration
- Connects to FastAPI backend for RAG-powered suggested replies
- Uses shared design system and UI primitives
- Demo-ready: enter a customer message and get a real AI-generated reply with sources

## Integration
- Consumes `/generate_reply` endpoint from the backend
- Easy to extend for real ticket/user context

## Dev
- `npm install`
- `npm run dev` (with backend running)
- Configure `BACKEND_URL` in `.env` if needed
