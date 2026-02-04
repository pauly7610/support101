"""
Support Agent Blueprint - RAG-powered customer support agent.

Integrates with existing RAGChain for knowledge retrieval and
provides structured support workflows.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..core.agent_registry import AgentBlueprint
from ..core.base_agent import AgentConfig, AgentState, AgentStatus, BaseAgent, Tool

# Type hints for optional dependencies
RAGChainType = Any
EmbeddingModelType = Any


class SupportAgent(BaseAgent):
    """
    RAG-powered support agent that handles customer queries.

    Workflow:
    1. Analyze query intent
    2. Retrieve relevant documentation
    3. Generate response with citations
    4. Assess confidence and escalate if needed
    """

    INTENT_PROMPT = ChatPromptTemplate.from_template(
        "Analyze the following customer support query and classify its intent.\n"
        "Categories: billing, technical, account, product, general, complaint\n"
        "Also assess urgency: low, medium, high, critical\n\n"
        "Query: {query}\n\n"
        'Respond in JSON format: {{"intent": "...", "urgency": "...", "keywords": [...]}}'
    )

    RESPONSE_PROMPT = ChatPromptTemplate.from_template(
        "You are a helpful customer support agent.\n"
        "Based on the following context from our documentation, provide a helpful response.\n"
        "If you cannot answer confidently, indicate that escalation may be needed.\n\n"
        "Context:\n{context}\n\n"
        "Customer Query: {query}\n\n"
        "Previous conversation:\n{history}\n\n"
        "Provide a helpful, empathetic response:"
    )

    def __init__(
        self,
        config: AgentConfig,
        rag_chain: Optional[RAGChainType] = None,
        llm: Optional[Any] = None,
        embedding_model: Optional[EmbeddingModelType] = None,
    ) -> None:
        """
        Initialize SupportAgent with optional dependency injection.

        Args:
            config: Agent configuration
            rag_chain: Optional RAGChain instance (lazy-loaded if not provided)
            llm: Optional LLM instance (lazy-loaded if not provided)
            embedding_model: Optional embedding model (lazy-loaded if not provided)
        """
        super().__init__(config)
        self._rag_chain = rag_chain
        self._llm = llm
        self._embedding_model = embedding_model
        self._initialized = False
        self._register_default_tools()

    def _lazy_init(self) -> None:
        """Lazy initialization of LLM dependencies."""
        if self._initialized:
            return

        if self._rag_chain is None:
            try:
                from packages.llm_engine.chains.rag_chain import RAGChain

                self._rag_chain = RAGChain()
            except ImportError:
                pass

        if self._llm is None:
            try:
                self._llm = ChatOpenAI(temperature=0.3)
            except Exception:
                pass

        if self._embedding_model is None:
            try:
                from packages.llm_engine.embeddings import get_fastembed_model

                self._embedding_model = get_fastembed_model()
            except ImportError:
                pass

        self._initialized = True

    @property
    def rag_chain(self) -> Optional[RAGChainType]:
        """Get RAG chain, initializing if needed."""
        self._lazy_init()
        return self._rag_chain

    @property
    def llm(self) -> Optional[Any]:
        """Get LLM, initializing if needed."""
        self._lazy_init()
        return self._llm

    @property
    def embedding_model(self) -> Optional[EmbeddingModelType]:
        """Get embedding model, initializing if needed."""
        self._lazy_init()
        return self._embedding_model

    def _register_default_tools(self) -> None:
        """Register default tools for support operations."""
        self.register_tool(
            Tool(
                name="search_knowledge_base",
                description="Search the knowledge base for relevant documentation",
                func=self._search_knowledge_base,
            )
        )
        self.register_tool(
            Tool(
                name="escalate_to_human",
                description="Escalate the ticket to a human agent",
                func=self._escalate_to_human,
                requires_approval=True,
            )
        )
        self.register_tool(
            Tool(
                name="create_ticket",
                description="Create a support ticket for follow-up",
                func=self._create_ticket,
            )
        )

    async def _search_knowledge_base(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search knowledge base using RAG."""
        try:
            from packages.llm_engine.vector_store import query_pinecone
        except ImportError:
            return [{"content": "Knowledge base unavailable", "source": "", "score": 0.0}]

        if self.embedding_model is None:
            return [{"content": "Embedding model unavailable", "source": "", "score": 0.0}]

        results = await query_pinecone(
            query_text=query,
            embedding_model=self.embedding_model,
            top_k=top_k,
        )
        return [
            {
                "content": r.get("metadata", {}).get("text", ""),
                "source": r.get("metadata", {}).get("source_url", ""),
                "score": r.get("score", 0.0),
            }
            for r in results
        ]

    async def _escalate_to_human(self, reason: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Escalate to human agent."""
        return {
            "escalated": True,
            "reason": reason,
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _create_ticket(
        self, subject: str, description: str, priority: str = "medium"
    ) -> Dict[str, Any]:
        """Create a support ticket."""
        return {
            "ticket_created": True,
            "subject": subject,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def plan(self, state: AgentState) -> Dict[str, Any]:
        """Determine next action based on current state."""
        step = state.current_step

        if step == 0:
            return {
                "action": "analyze_intent",
                "action_input": {"query": state.input_data.get("query", "")},
            }
        elif step == 1:
            return {
                "action": "search_knowledge_base",
                "action_input": {
                    "query": state.input_data.get("query", ""),
                    "intent": state.intermediate_steps[-1].get("intent", {}),
                },
            }
        elif step == 2:
            return {
                "action": "generate_response",
                "action_input": {
                    "query": state.input_data.get("query", ""),
                    "context": state.intermediate_steps[-1].get("results", []),
                },
            }
        elif step == 3:
            last_response = state.intermediate_steps[-1]
            if last_response.get("confidence", 1.0) < self.config.confidence_threshold:
                return {
                    "action": "escalate_to_human",
                    "action_input": {
                        "reason": "Low confidence response",
                        "context": last_response,
                    },
                    "requires_approval": True,
                }
            return {"action": "complete", "action_input": {}}

        return {"action": "complete", "action_input": {}}

    async def execute_step(self, state: AgentState, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step."""
        action_name = action.get("action")
        action_input = action.get("action_input", {})

        if action_name == "analyze_intent":
            return await self._analyze_intent(action_input["query"])

        elif action_name == "search_knowledge_base":
            results = await self._search_knowledge_base(action_input["query"])
            return {"action": "search_knowledge_base", "results": results}

        elif action_name == "generate_response":
            return await self._generate_response(
                action_input["query"],
                action_input["context"],
                state.input_data.get("history", []),
            )

        elif action_name == "escalate_to_human":
            result = await self._escalate_to_human(
                action_input["reason"],
                action_input["context"],
            )
            state.output_data["escalation"] = result
            return {"action": "escalate_to_human", **result}

        elif action_name == "complete":
            return {"action": "complete", "completed": True}

        return {"action": action_name, "error": "Unknown action"}

    async def _analyze_intent(self, query: str) -> Dict[str, Any]:
        """Analyze query intent using LLM."""
        try:
            chain = self.INTENT_PROMPT | self.llm
            result = await chain.ainvoke({"query": query})
            import json

            intent_data = json.loads(result.content)
            return {"action": "analyze_intent", "intent": intent_data}
        except Exception as e:
            return {
                "action": "analyze_intent",
                "intent": {"intent": "general", "urgency": "medium", "keywords": []},
                "error": str(e),
            }

    async def _generate_response(
        self,
        query: str,
        context: List[Dict[str, Any]],
        history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Generate response using RAG context."""
        context_str = "\n\n".join(
            [f"[Source: {c.get('source', 'Unknown')}]\n{c.get('content', '')}" for c in context]
        )

        history_str = (
            "\n".join(
                [f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in history[-5:]]
            )
            if history
            else "No previous conversation"
        )

        chain = self.RESPONSE_PROMPT | self.llm
        result = await chain.ainvoke(
            {
                "query": query,
                "context": context_str,
                "history": history_str,
            }
        )

        avg_score = sum(c.get("score", 0) for c in context) / len(context) if context else 0

        return {
            "action": "generate_response",
            "response": result.content,
            "confidence": avg_score,
            "sources": [c.get("source") for c in context if c.get("source")],
        }

    def should_continue(self, state: AgentState) -> bool:
        """Check if agent should continue."""
        if state.current_step >= self.config.max_iterations:
            return False
        if state.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.AWAITING_HUMAN]:
            return False
        if state.intermediate_steps and state.intermediate_steps[-1].get("action") == "complete":
            return False
        return True


SupportAgentBlueprint = AgentBlueprint(
    name="support_agent",
    agent_class=SupportAgent,
    description="RAG-powered customer support agent with intent analysis and escalation",
    default_config={
        "max_iterations": 5,
        "timeout_seconds": 60,
        "confidence_threshold": 0.75,
        "require_human_approval": False,
    },
    required_tools=["search_knowledge_base", "escalate_to_human"],
    version="1.0.0",
)
