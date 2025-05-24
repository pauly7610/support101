🧠 Support Intelligence Core (SIC) — Monorepo
A modular, LLM-powered customer support platform designed for rapid deployment and internal extensibility.

Includes:

🚀 FastAPI backend (LangChain RAG, ingestion pipeline, Pinecone, HuggingFace or OpenAI)

🧑‍💼 Agent Copilot: Chrome extension that embeds in Zendesk/Intercom

💬 Customer Chatbot: Website widget (Next.js + Tailwind)

🧩 Shared models, chains, telemetry, and design system across all apps

Built for speed, reusability, and modularity — to help you build vs. buy with confidence.

📁 Monorepo Structure
bash
Copy
Edit
support-core/
├── apps/
│   ├── backend/           # FastAPI API (RAG, ingestion, LLM)
│   ├── agent-copilot/     # React Chrome Extension for agent support
│   └── customer-bot/      # Next.js Chatbot widget
├── packages/
│   ├── shared/            # Pydantic models, constants, utils
│   ├── llm-engine/        # LangChain chains, vector store, prompts
│   └── observability/     # LangSmith, PromptLayer, OpenTelemetry hooks
├── .env.template
├── docker-compose.yml
├── turbo.json
└── README.md (you are here)
🔑 Key Features
📚 Retrieval-Augmented Generation (RAG)
Query embedding + document search via Pinecone

Context-aware generation using HuggingFace or OpenAI LLMs

Source citation for all responses

🔄 Documentation Ingestion
Ingest content from public URLs (e.g., Firecrawl-ready)

Chunk, embed, and store content with /ingest_documentation

Markdown & semantic chunking support

🧑‍💻 Agent Copilot (Chrome Extension)
Injected into Zendesk or Intercom UI

Auto-detects customer query or lets agent paste it in

Shows suggested reply + source documents

Easy copy-paste to reply

💬 Customer Chatbot
Embeddable floating widget

Asks user questions → backend RAG → shows instant answers

Cites doc links for full context

🛠 Shared Infrastructure
Shared Pydantic models for contracts across frontend/backend

Shared telemetry via LangSmith + PromptLayer

Modular LangChain chains for RAG and memory

Unified UI design system (via DESIGN_SYSTEM.md)

⚡ Quickstart
1. Clone + Setup Environment
bash
Copy
Edit
git clone https://github.com/pauly7610/support101
cd support101
cp .env.template .env
Fill in values for:

PINECONE_API_KEY

FIRECRAWL_API_KEY

HUGGINGFACE_API_KEY (or OpenAI)

LANGSMITH_API_KEY, etc.

2. Install Dependencies
Backend

bash
Copy
Edit
cd apps/backend
pip install -r requirements.txt
Frontends

bash
Copy
Edit
cd apps/agent-copilot && npm install
cd apps/customer-bot && npm install
3. Run Locally
Backend

bash
Copy
Edit
uvicorn apps.backend.main:app --reload
Agent Copilot Extension

bash
Copy
Edit
cd apps/agent-copilot
npm run dev
Customer Bot Widget

bash
Copy
Edit
cd apps/customer-bot
npm run dev
4. Test It Out
Visit a helpdesk page with the extension running — see the Copilot sidebar

Open the website widget → ask a question

Both hit /generate_reply → get grounded answers with source docs

📡 API Endpoints
Method	Route	Description
GET	/health	Simple health check
POST	/generate_reply	Main endpoint for LLM reply generation
POST	/ingest_documentation	Crawl & embed new doc content

🧠 Developer Notes
See individual app README.mds for dev details

Uses Turborepo for task orchestration

Docker support in docker-compose.yml (coming soon)

Add new chains or document loaders in packages/llm-engine

Extend observability in packages/observability

🚀 Deployment
 Railway, Render, or AWS-compatible with Docker

 Add CI via GitHub Actions (lint/test/build)

 Staging + production config via env vars

📐 Resources
DESIGN_SYSTEM.md: Shared UI guidelines + tokens

packages/shared: Source of truth for all models/types

turbo.json: Task graph for multi-app orchestration

