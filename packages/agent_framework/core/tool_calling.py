"""
Structured Tool Calling for Agent Blueprints.

Replaces prompt-based parsing with native LLM tool_call / function_calling
for reliable, type-safe tool invocation. Supports OpenAI, Anthropic, and
any provider that implements the tool_call spec.

Usage:
    from packages.agent_framework.core.tool_calling import (
        ToolDefinition, ToolRegistry, execute_tool_calls,
    )

    registry = ToolRegistry()

    @registry.tool(
        name="search_knowledge_base",
        description="Search the KB for relevant docs",
        parameters={
            "query": {"type": "string", "description": "Search query"},
            "top_k": {"type": "integer", "description": "Results count"},
        },
    )
    async def search_kb(query: str, top_k: int = 5) -> dict:
        return await vector_store.search(query, top_k)

    # Convert to LLM-native format
    openai_tools = registry.to_openai_tools()
    anthropic_tools = registry.to_anthropic_tools()

    # Execute tool calls from LLM response
    results = await execute_tool_calls(registry, tool_calls)
"""

import asyncio
import inspect
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class ToolParameter:
    """Schema for a single tool parameter."""

    name: str
    type: str
    description: str = ""
    required: bool = True
    enum: Optional[List[str]] = None
    default: Any = None


@dataclass
class ToolDefinition:
    """Complete definition of a callable tool."""

    name: str
    description: str
    parameters: Dict[str, Dict[str, Any]]
    required_params: List[str] = field(default_factory=list)
    handler: Optional[Callable] = None

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []

        for param_name, param_schema in self.parameters.items():
            prop: Dict[str, Any] = {"type": param_schema.get("type", "string")}
            if "description" in param_schema:
                prop["description"] = param_schema["description"]
            if "enum" in param_schema:
                prop["enum"] = param_schema["enum"]
            properties[param_name] = prop

            if param_name in self.required_params:
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_anthropic_schema(self) -> Dict[str, Any]:
        """Convert to Anthropic tool use format."""
        properties = {}
        required = []

        for param_name, param_schema in self.parameters.items():
            prop: Dict[str, Any] = {"type": param_schema.get("type", "string")}
            if "description" in param_schema:
                prop["description"] = param_schema["description"]
            if "enum" in param_schema:
                prop["enum"] = param_schema["enum"]
            properties[param_name] = prop

            if param_name in self.required_params:
                required.append(param_name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


@dataclass
class ToolCall:
    """Represents a tool call from an LLM response."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool call."""

    tool_call_id: str
    name: str
    content: str
    is_error: bool = False


class ToolRegistry:
    """
    Registry for structured tools that can be invoked by LLMs.

    Provides decorators for registering tools and methods for
    converting to provider-specific formats.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Dict[str, Any]],
        required: Optional[List[str]] = None,
    ) -> Callable:
        """Decorator to register a function as a structured tool."""
        def decorator(func: Callable) -> Callable:
            # Auto-detect required params from function signature
            sig = inspect.signature(func)
            auto_required = []
            for param_name, param in sig.parameters.items():
                if param_name in parameters and param.default is inspect.Parameter.empty:
                    auto_required.append(param_name)

            tool_def = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                required_params=required or auto_required,
                handler=func,
            )
            self._tools[name] = tool_def
            return func
        return decorator

    def register(self, tool_def: ToolDefinition) -> None:
        """Register a pre-built ToolDefinition."""
        self._tools[tool_def.name] = tool_def

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())

    def to_openai_tools(self) -> List[Dict[str, Any]]:
        """Convert all tools to OpenAI function calling format."""
        return [t.to_openai_schema() for t in self._tools.values()]

    def to_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Convert all tools to Anthropic tool use format."""
        return [t.to_anthropic_schema() for t in self._tools.values()]

    def to_langchain_tools(self) -> List[Dict[str, Any]]:
        """Convert to LangChain tool format (same as OpenAI)."""
        return self.to_openai_tools()


async def execute_tool_call(
    registry: ToolRegistry,
    tool_call: ToolCall,
) -> ToolResult:
    """
    Execute a single tool call using the registry.

    Args:
        registry: Tool registry containing handlers
        tool_call: The tool call to execute

    Returns:
        ToolResult with the output or error
    """
    tool_def = registry.get(tool_call.name)
    if not tool_def or not tool_def.handler:
        return ToolResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            content=json.dumps({
                "error": f"Unknown tool: {tool_call.name}",
                "available_tools": [t.name for t in registry.list_tools()],
            }),
            is_error=True,
        )

    try:
        handler = tool_def.handler
        if asyncio.iscoroutinefunction(handler):
            result = await handler(**tool_call.arguments)
        else:
            result = handler(**tool_call.arguments)

        content = json.dumps(result, default=str) if not isinstance(result, str) else result

        return ToolResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            content=content,
        )
    except TypeError as e:
        return ToolResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            content=json.dumps({
                "error": f"Invalid arguments for {tool_call.name}: {e}",
                "provided_args": list(tool_call.arguments.keys()),
                "expected_params": list(tool_def.parameters.keys()),
            }),
            is_error=True,
        )
    except Exception as e:
        logger.error("Tool execution error for %s: %s", tool_call.name, e)
        return ToolResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            content=json.dumps({
                "error_type": "tool_execution_error",
                "message": str(e)[:500],
                "retryable": True,
            }),
            is_error=True,
        )


async def execute_tool_calls(
    registry: ToolRegistry,
    tool_calls: List[ToolCall],
    parallel: bool = True,
) -> List[ToolResult]:
    """
    Execute multiple tool calls, optionally in parallel.

    Args:
        registry: Tool registry containing handlers
        tool_calls: List of tool calls to execute
        parallel: Whether to execute in parallel (default: True)

    Returns:
        List of ToolResults in the same order as input
    """
    if not tool_calls:
        return []

    if parallel:
        tasks = [execute_tool_call(registry, tc) for tc in tool_calls]
        return await asyncio.gather(*tasks)
    else:
        results = []
        for tc in tool_calls:
            result = await execute_tool_call(registry, tc)
            results.append(result)
        return results


def parse_openai_tool_calls(response_message: Dict[str, Any]) -> List[ToolCall]:
    """
    Parse tool calls from an OpenAI API response message.

    Args:
        response_message: The message object from OpenAI's response

    Returns:
        List of ToolCall objects
    """
    raw_calls = response_message.get("tool_calls", [])
    calls = []
    for tc in raw_calls:
        try:
            args = tc.get("function", {}).get("arguments", "{}")
            if isinstance(args, str):
                args = json.loads(args)
            calls.append(ToolCall(
                id=tc.get("id", ""),
                name=tc.get("function", {}).get("name", ""),
                arguments=args,
            ))
        except json.JSONDecodeError:
            logger.warning("Failed to parse tool call arguments: %s", tc)
    return calls


def parse_anthropic_tool_calls(content_blocks: List[Dict[str, Any]]) -> List[ToolCall]:
    """
    Parse tool calls from an Anthropic API response.

    Args:
        content_blocks: The content array from Anthropic's response

    Returns:
        List of ToolCall objects
    """
    calls = []
    for block in content_blocks:
        if block.get("type") == "tool_use":
            calls.append(ToolCall(
                id=block.get("id", ""),
                name=block.get("name", ""),
                arguments=block.get("input", {}),
            ))
    return calls


# ── Built-in Support Tools ───────────────────────────────────────

def create_support_tool_registry() -> ToolRegistry:
    """
    Create a ToolRegistry pre-loaded with common support tools.

    These tools are available to all agent blueprints by default.
    """
    registry = ToolRegistry()

    @registry.tool(
        name="search_knowledge_base",
        description="Search the knowledge base for documents relevant to a customer query. Returns matching excerpts with confidence scores.",
        parameters={
            "query": {"type": "string", "description": "The search query"},
            "top_k": {"type": "integer", "description": "Number of results to return (1-20, default: 5)"},
        },
    )
    async def search_kb(query: str, top_k: int = 5) -> Dict[str, Any]:
        try:
            from packages.llm_engine.vector_store import query_pinecone
            from packages.llm_engine.embeddings import get_fastembed_model
            model = get_fastembed_model()
            results = await query_pinecone(query_text=query, embedding_model=model, top_k=top_k)
            return {
                "results": [
                    {
                        "score": r.get("score", 0),
                        "text": r.get("metadata", {}).get("text", "")[:500],
                        "source_url": r.get("metadata", {}).get("source_url", ""),
                    }
                    for r in results
                ],
            }
        except Exception as e:
            return {"error": str(e)[:200], "results": []}

    @registry.tool(
        name="escalate_to_human",
        description="Escalate the current ticket to a human agent. Use when the query is too complex, sensitive, or outside the agent's capabilities.",
        parameters={
            "reason": {"type": "string", "description": "Why this needs human review"},
            "priority": {
                "type": "string",
                "description": "Escalation priority",
                "enum": ["critical", "high", "medium", "low"],
            },
            "ticket_id": {"type": "string", "description": "The ticket ID to escalate"},
        },
    )
    async def escalate(reason: str, priority: str = "medium", ticket_id: str = "") -> Dict[str, Any]:
        return {
            "status": "escalated",
            "reason": reason,
            "priority": priority,
            "ticket_id": ticket_id,
            "message": "Ticket has been escalated to the human review queue.",
        }

    @registry.tool(
        name="get_customer_context",
        description="Retrieve context about a customer including their recent tickets, account status, and interaction history.",
        parameters={
            "customer_id": {"type": "string", "description": "The customer's ID"},
            "include_history": {"type": "boolean", "description": "Whether to include interaction history (default: true)"},
        },
    )
    async def get_customer(customer_id: str, include_history: bool = True) -> Dict[str, Any]:
        return {
            "customer_id": customer_id,
            "status": "active",
            "tier": "professional",
            "recent_tickets": [],
            "history_included": include_history,
            "note": "Customer context retrieval — connect to CRM for live data.",
        }

    @registry.tool(
        name="draft_response",
        description="Draft a response to send to the customer. The response will be queued for human review if HITL is enabled.",
        parameters={
            "content": {"type": "string", "description": "The response text to send"},
            "tone": {
                "type": "string",
                "description": "Desired tone",
                "enum": ["professional", "friendly", "empathetic", "technical"],
            },
            "include_sources": {"type": "boolean", "description": "Whether to include source citations"},
        },
    )
    async def draft_response(
        content: str, tone: str = "professional", include_sources: bool = True
    ) -> Dict[str, Any]:
        return {
            "draft": content,
            "tone": tone,
            "sources_included": include_sources,
            "status": "pending_review",
        }

    return registry
