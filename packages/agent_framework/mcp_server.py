"""
MCP (Model Context Protocol) Server for the Agent Framework.

Exposes agent capabilities as MCP tools, making the framework interoperable
with Claude, Cursor, Windsurf, and any MCP-compatible client.

Tools exposed:
- suggest_reply: Generate a support reply using RAG
- search_knowledge_base: Search the vector store for relevant documents
- list_agents: List available agents and their status
- execute_agent: Execute a specific agent with input data
- search_golden_paths: Search for proven resolution patterns
- suggest_playbook: Get playbook suggestions for a ticket
- get_hitl_queue: View the human-in-the-loop review queue
- get_governance_dashboard: View governance metrics

Usage:
    python -m packages.agent_framework.mcp_server
"""

import asyncio
import json
import sys
from typing import Any

# MCP protocol types — lightweight implementation that follows the spec
# without requiring the official SDK (which may not be installed)


class MCPServer:
    """
    Lightweight MCP server implementing the JSON-RPC 2.0 transport
    over stdio, following the Model Context Protocol specification.
    """

    def __init__(self) -> None:
        self.tools: dict[str, dict[str, Any]] = {}
        self.handlers: dict[str, Any] = {}
        self._framework = None
        self._rag_chain = None

    def tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
    ):
        """Decorator to register an MCP tool."""

        def decorator(func):
            self.tools[name] = {
                "name": name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": parameters,
                },
            }
            self.handlers[name] = func
            return func

        return decorator

    async def _get_framework(self):
        """Lazy-load the AgentFramework SDK."""
        if self._framework is None:
            try:
                from packages.agent_framework.sdk import AgentFramework

                self._framework = AgentFramework()
                await self._framework.start()
            except Exception:
                self._framework = None
        return self._framework

    async def _get_rag_chain(self):
        """Lazy-load the RAG chain."""
        if self._rag_chain is None:
            try:
                from packages.llm_engine.chains.rag_chain import RAGChain

                self._rag_chain = RAGChain()
            except Exception:
                self._rag_chain = None
        return self._rag_chain

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle a JSON-RPC 2.0 request."""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return self._response(
                req_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": "support101-agent-framework",
                        "version": "1.0.0",
                    },
                },
            )

        elif method == "notifications/initialized":
            return None  # No response for notifications

        elif method == "tools/list":
            return self._response(
                req_id,
                {
                    "tools": list(self.tools.values()),
                },
            )

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            handler = self.handlers.get(tool_name)
            if not handler:
                return self._error(req_id, -32601, f"Unknown tool: {tool_name}")
            try:
                result = await handler(arguments)
                return self._response(
                    req_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2, default=str),
                            },
                        ],
                    },
                )
            except Exception as e:
                return self._response(
                    req_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "error_type": "tool_execution_error",
                                        "message": str(e)[:500],
                                        "retryable": True,
                                        "documentation": "https://api.support101/errors#E500",
                                    },
                                    indent=2,
                                ),
                            },
                        ],
                        "isError": True,
                    },
                )

        elif method == "ping":
            return self._response(req_id, {})

        else:
            return self._error(req_id, -32601, f"Method not found: {method}")

    def _response(self, req_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _error(self, req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }

    async def run_stdio(self) -> None:
        """Run the MCP server over stdio transport."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin.buffer)

        (
            writer_transport,
            writer_protocol,
        ) = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout.buffer
        )
        writer = asyncio.StreamWriter(
            writer_transport, writer_protocol, None, asyncio.get_event_loop()
        )

        while True:
            try:
                line = await reader.readline()
                if not line:
                    break
                line = line.decode("utf-8").strip()
                if not line:
                    continue
                request = json.loads(line)
                response = await self.handle_request(request)
                if response is not None:
                    out = json.dumps(response) + "\n"
                    writer.write(out.encode("utf-8"))
                    await writer.drain()
            except json.JSONDecodeError:
                continue
            except Exception:
                break


# ── Server Instance & Tool Registration ──────────────────────────

server = MCPServer()


@server.tool(
    name="suggest_reply",
    description="Generate a support reply for a customer query using RAG (Retrieval-Augmented Generation). Returns a suggested reply with source citations.",
    parameters={
        "query": {
            "type": "string",
            "description": "The customer's question or support ticket content",
        },
        "ticket_id": {
            "type": "string",
            "description": "Optional ticket ID for context",
        },
    },
)
async def suggest_reply(args: dict[str, Any]) -> dict[str, Any]:
    chain = await server._get_rag_chain()
    if not chain:
        return {
            "reply_text": None,
            "error": "RAG chain not available. Check LLM engine configuration.",
        }
    result = await chain.generate(args.get("query", ""))
    return result


@server.tool(
    name="search_knowledge_base",
    description="Search the knowledge base (Pinecone vector store) for documents relevant to a query. Returns matching excerpts with confidence scores.",
    parameters={
        "query": {"type": "string", "description": "Search query"},
        "top_k": {
            "type": "integer",
            "description": "Number of results to return (default: 5)",
        },
    },
)
async def search_knowledge_base(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from packages.llm_engine.embeddings import get_fastembed_model
        from packages.llm_engine.vector_store import query_pinecone

        model = get_fastembed_model()
        results = await query_pinecone(
            query_text=args.get("query", ""),
            embedding_model=model,
            top_k=args.get("top_k", 5),
        )
        return {
            "results": [
                {
                    "score": r.get("score", 0),
                    "text": r.get("metadata", {}).get("text", "")[:500],
                    "source_url": r.get("metadata", {}).get("source_url", ""),
                }
                for r in results
            ],
            "total": len(results),
        }
    except Exception as e:
        return {"results": [], "error": str(e)[:200]}


@server.tool(
    name="list_agents",
    description="List all registered agents in the framework, optionally filtered by tenant or blueprint.",
    parameters={
        "tenant_id": {"type": "string", "description": "Optional tenant ID filter"},
        "blueprint_name": {
            "type": "string",
            "description": "Optional blueprint name filter",
        },
    },
)
async def list_agents(args: dict[str, Any]) -> dict[str, Any]:
    framework = await server._get_framework()
    if not framework:
        return {"agents": [], "error": "Agent framework not available"}
    try:
        from packages.agent_framework.core.registry import AgentRegistry

        registry = AgentRegistry()
        agents = registry.list_agents(
            tenant_id=args.get("tenant_id"),
            blueprint_name=args.get("blueprint_name"),
        )
        return {"agents": [a.to_dict() if hasattr(a, "to_dict") else str(a) for a in agents]}
    except Exception as e:
        return {"agents": [], "error": str(e)[:200]}


@server.tool(
    name="execute_agent",
    description="Execute a specific agent with input data. The agent will process the input using its blueprint's tools and return a result.",
    parameters={
        "agent_id": {"type": "string", "description": "The ID of the agent to execute"},
        "input_data": {"type": "object", "description": "Input data for the agent"},
    },
)
async def execute_agent(args: dict[str, Any]) -> dict[str, Any]:
    framework = await server._get_framework()
    if not framework:
        return {"error": "Agent framework not available"}
    try:
        result = await framework.execute(
            agent_id=args.get("agent_id", ""),
            input_data=args.get("input_data", {}),
        )
        return result if isinstance(result, dict) else {"result": str(result)}
    except Exception as e:
        return {"error": str(e)[:200]}


@server.tool(
    name="search_golden_paths",
    description="Search for proven resolution patterns (golden paths) that match a query. Golden paths are successful resolutions stored from HITL feedback.",
    parameters={
        "query": {
            "type": "string",
            "description": "The support query to find golden paths for",
        },
        "top_k": {"type": "integer", "description": "Number of results (default: 3)"},
    },
)
async def search_golden_paths(args: dict[str, Any]) -> dict[str, Any]:
    framework = await server._get_framework()
    if not framework:
        return {"golden_paths": [], "error": "Agent framework not available"}
    try:
        results = await framework.search_golden_paths(
            query=args.get("query", ""),
            top_k=args.get("top_k", 3),
        )
        return {"golden_paths": results}
    except Exception as e:
        return {"golden_paths": [], "error": str(e)[:200]}


@server.tool(
    name="suggest_playbook",
    description="Get playbook suggestions for handling a support ticket. Playbooks are derived from successful resolution patterns in the activity graph.",
    parameters={
        "ticket_content": {
            "type": "string",
            "description": "The ticket content to find playbooks for",
        },
        "category": {"type": "string", "description": "Optional ticket category"},
    },
)
async def suggest_playbook(args: dict[str, Any]) -> dict[str, Any]:
    framework = await server._get_framework()
    if not framework:
        return {"playbooks": [], "error": "Agent framework not available"}
    try:
        results = await framework.suggest_playbook(
            query=args.get("ticket_content", ""),
        )
        return {"playbooks": results}
    except Exception as e:
        return {"playbooks": [], "error": str(e)[:200]}


@server.tool(
    name="get_hitl_queue",
    description="View the human-in-the-loop review queue. Shows pending items that need human review before being sent to customers.",
    parameters={
        "status_filter": {
            "type": "string",
            "description": "Filter by status: pending, assigned, completed",
        },
        "limit": {
            "type": "integer",
            "description": "Max items to return (default: 20)",
        },
    },
)
async def get_hitl_queue(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from packages.agent_framework.hitl.manager import HITLManager

        manager = HITLManager()
        items = manager.get_queue(
            status_filter=args.get("status_filter"),
            limit=args.get("limit", 20),
        )
        return {
            "items": [i.to_dict() if hasattr(i, "to_dict") else str(i) for i in items],
            "total": len(items),
        }
    except Exception as e:
        return {"items": [], "error": str(e)[:200]}


@server.tool(
    name="get_governance_dashboard",
    description="View governance dashboard metrics including active agents, compliance status, and audit summary.",
    parameters={
        "tenant_id": {"type": "string", "description": "Optional tenant ID filter"},
    },
)
async def get_governance_dashboard(args: dict[str, Any]) -> dict[str, Any]:
    try:
        from packages.agent_framework.core.registry import AgentRegistry
        from packages.agent_framework.governance.audit import AuditLogger

        registry = AgentRegistry()
        audit = AuditLogger()
        agents = registry.list_agents(tenant_id=args.get("tenant_id"))
        stats = audit.get_stats(tenant_id=args.get("tenant_id"))
        return {
            "total_agents": len(agents),
            "active_agents": len([a for a in agents if getattr(a, "status", "") == "active"]),
            "audit_stats": stats if isinstance(stats, dict) else {},
        }
    except Exception as e:
        return {"error": str(e)[:200]}


# ── Entry Point ──────────────────────────────────────────────────


async def main() -> None:
    """Run the MCP server."""
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
