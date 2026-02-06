"""
FastAPI router for A2A Protocol endpoints.

Exposes:
- GET  /.well-known/agent.json  — Agent Card discovery
- POST /a2a                     — JSON-RPC 2.0 task dispatch
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter

from .protocol import A2AServer, AgentCard, AgentSkill

logger = logging.getLogger(__name__)

router = APIRouter(tags=["A2A Protocol"])

BASE_URL = os.getenv("A2A_BASE_URL", "http://localhost:8000")

# ── Agent Card ───────────────────────────────────────────────────

_agent_card = AgentCard(
    name="Support101 Agent",
    description=(
        "AI-powered customer support agent with RAG, knowledge base search, "
        "ticket triage, escalation, and playbook execution capabilities."
    ),
    url=f"{BASE_URL}/a2a",
    version="1.0.0",
    skills=[
        AgentSkill(
            id="suggest_reply",
            name="Suggest Reply",
            description="Generate a support reply for a customer query using RAG with source citations.",
            tags=["support", "rag", "reply"],
            examples=[
                "How do I reset my password?",
                "What are the pricing tiers?",
                "I need help with billing.",
            ],
        ),
        AgentSkill(
            id="search_knowledge_base",
            name="Search Knowledge Base",
            description="Search the vector store for documents relevant to a query.",
            tags=["search", "knowledge", "docs"],
            examples=[
                "Find documentation about SSO setup",
                "Search for API rate limit info",
            ],
        ),
        AgentSkill(
            id="triage_ticket",
            name="Triage Ticket",
            description="Classify and prioritize a support ticket, suggest routing.",
            tags=["triage", "classification", "routing"],
            examples=[
                "Customer reports login failure after password change",
                "Billing discrepancy on enterprise account",
            ],
        ),
        AgentSkill(
            id="execute_playbook",
            name="Execute Playbook",
            description="Run a proven resolution playbook for a known issue pattern.",
            tags=["playbook", "automation", "resolution"],
            examples=[
                "Run the password reset playbook",
                "Execute the billing dispute resolution flow",
            ],
        ),
    ],
    capabilities={
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": True,
    },
    authentication={
        "schemes": ["bearer"],
        "credentials": "JWT token from /login endpoint",
    },
)

# ── A2A Server Instance ──────────────────────────────────────────

_server = A2AServer(_agent_card)


async def _handle_suggest_reply(query: str, metadata: dict[str, Any]) -> str:
    """Handler for suggest_reply skill."""
    try:
        from packages.llm_engine.chains.rag_chain import RAGChain

        chain = RAGChain()
        result = await chain.generate(query)
        if "error_type" in result:
            return f"Error: {result.get('message', 'Unknown error')}"
        reply = result.get("reply", "No response generated.")
        sources = result.get("sources", [])
        if sources:
            citations = "\n\nSources:\n" + "\n".join(
                f"- [{s.get('url', '')}] (confidence: {s.get('confidence', 0):.0%})"
                for s in sources
            )
            return reply + citations
        return reply
    except ImportError:
        return f"[Mock] Suggested reply for: {query[:200]}"


async def _handle_search_kb(query: str, metadata: dict[str, Any]) -> str:
    """Handler for search_knowledge_base skill."""
    try:
        from packages.llm_engine.embeddings import get_fastembed_model
        from packages.llm_engine.vector_store import query_pinecone

        model = get_fastembed_model()
        results = await query_pinecone(query_text=query, embedding_model=model, top_k=5)
        if not results:
            return "No relevant documents found."
        lines = []
        for i, r in enumerate(results, 1):
            score = r.get("score", 0)
            text = r.get("metadata", {}).get("text", "")[:300]
            url = r.get("metadata", {}).get("source_url", "")
            lines.append(f"{i}. [{url}] (score: {score:.2f})\n   {text}")
        return "\n\n".join(lines)
    except ImportError:
        return f"[Mock] KB search results for: {query[:200]}"


async def _handle_triage(query: str, metadata: dict[str, Any]) -> str:
    """Handler for triage_ticket skill."""
    return (
        f"Ticket triaged:\n"
        f"- Content: {query[:200]}\n"
        f"- Suggested priority: medium\n"
        f"- Suggested category: general_inquiry\n"
        f"- Suggested routing: tier_1_support\n"
        f"Note: Connect to classification model for production triage."
    )


async def _handle_playbook(query: str, metadata: dict[str, Any]) -> str:
    """Handler for execute_playbook skill."""
    try:
        from packages.agent_framework.learning.playbook_engine import PlaybookEngine

        engine = PlaybookEngine()
        suggestions = engine.suggest(query)
        if not suggestions:
            return "No matching playbook found for this query."
        return f"Playbook match: {suggestions[0]}"
    except ImportError:
        return f"[Mock] Playbook execution for: {query[:200]}"


# Register handlers
_server.register_handler("suggest_reply", _handle_suggest_reply)
_server.register_handler("search_knowledge_base", _handle_search_kb)
_server.register_handler("triage_ticket", _handle_triage)
_server.register_handler("execute_playbook", _handle_playbook)
_server.set_default_handler(_handle_suggest_reply)


# ── Routes ───────────────────────────────────────────────────────


@router.get("/.well-known/agent.json")
async def get_agent_card():
    """Serve the A2A Agent Card for discovery."""
    return JSONResponse(content=_agent_card.to_dict())


@router.post("/a2a")
async def a2a_endpoint(
    request: Request,
    _limiter: None = Depends(RateLimiter(times=30, seconds=60)),
):
    """
    A2A JSON-RPC 2.0 endpoint.

    Supported methods:
    - tasks/send: Create and execute a task
    - tasks/get: Retrieve a task by ID
    - tasks/cancel: Cancel a running task
    """
    body = await request.json()
    response = await _server.handle_jsonrpc(body)
    return JSONResponse(content=response)
