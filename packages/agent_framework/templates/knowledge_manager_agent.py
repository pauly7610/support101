"""
Knowledge Manager Agent Blueprint - Knowledge base curation and maintenance agent.

Curates, updates, deduplicates, and organizes knowledge base articles.
Identifies content gaps, stale articles, and conflicting information.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..core.agent_registry import AgentBlueprint
from ..core.base_agent import AgentConfig, AgentState, AgentStatus, BaseAgent, Tool

RAGChainType = Any
EmbeddingModelType = Any


class KnowledgeManagerAgent(BaseAgent):
    """
    Knowledge base curation and maintenance agent.

    Workflow:
    1. Audit existing knowledge base content
    2. Identify stale, duplicate, or conflicting articles
    3. Detect content gaps from recent support queries
    4. Generate update recommendations
    5. Request human approval for content changes
    """

    AUDIT_PROMPT = ChatPromptTemplate.from_template(
        "You are a knowledge base curator. Audit the following articles for quality.\n\n"
        "Articles:\n{articles}\n\n"
        "Evaluate each article and provide results in JSON format:\n"
        "{{\n"
        '  "audit_results": [\n'
        "    {{\n"
        '      "article_id": "...",\n'
        '      "title": "...",\n'
        '      "quality_score": 0-100,\n'
        '      "is_stale": true|false,\n'
        '      "issues": ["issue1"],\n'
        '      "recommendation": "keep|update|archive|merge"\n'
        "    }}\n"
        "  ],\n"
        '  "overall_health": 0-100,\n'
        '  "stale_count": 0,\n'
        '  "action_needed_count": 0\n'
        "}}"
    )

    GAP_ANALYSIS_PROMPT = ChatPromptTemplate.from_template(
        "You are a knowledge base analyst. Identify content gaps based on recent queries.\n\n"
        "Recent Unanswered Queries:\n{queries}\n\n"
        "Existing Article Topics:\n{existing_topics}\n\n"
        "Identify gaps in JSON format:\n"
        "{{\n"
        '  "gaps": [\n'
        "    {{\n"
        '      "topic": "...",\n'
        '      "query_count": 0,\n'
        '      "urgency": "high|medium|low",\n'
        '      "suggested_title": "...",\n'
        '      "suggested_outline": ["section1", "section2"]\n'
        "    }}\n"
        "  ],\n"
        '  "total_gaps": 0,\n'
        '  "coverage_score": 0-100\n'
        "}}"
    )

    DEDUP_PROMPT = ChatPromptTemplate.from_template(
        "You are a content deduplication specialist.\n"
        "Analyze the following articles for duplicates or overlapping content.\n\n"
        "Articles:\n{articles}\n\n"
        "Identify duplicates in JSON format:\n"
        "{{\n"
        '  "duplicate_groups": [\n'
        "    {{\n"
        '      "articles": ["id1", "id2"],\n'
        '      "similarity_score": 0-100,\n'
        '      "merge_recommendation": "merge into primary article",\n'
        '      "primary_article": "id1"\n'
        "    }}\n"
        "  ],\n"
        '  "total_duplicates": 0\n'
        "}}"
    )

    UPDATE_PROMPT = ChatPromptTemplate.from_template(
        "You are a technical writer updating a knowledge base article.\n\n"
        "Current Article:\n{current_content}\n\n"
        "Update Reason: {reason}\n"
        "Additional Context: {context}\n\n"
        "Generate the updated article in JSON format:\n"
        "{{\n"
        '  "title": "...",\n'
        '  "content": "updated article content in markdown",\n'
        '  "summary_of_changes": "what was changed and why",\n'
        '  "tags": ["tag1", "tag2"],\n'
        '  "confidence": 0-100\n'
        "}}"
    )

    def __init__(
        self,
        config: AgentConfig,
        llm: Optional[Any] = None,
        rag_chain: Optional[RAGChainType] = None,
    ) -> None:
        super().__init__(config)
        self._llm = llm
        self._rag_chain = rag_chain
        self._initialized = False
        self._register_default_tools()

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        if self._llm is None:
            try:
                self._llm = ChatOpenAI(temperature=0.2)
            except Exception:
                pass
        self._initialized = True

    @property
    def llm(self) -> Optional[Any]:
        self._lazy_init()
        return self._llm

    def _register_default_tools(self) -> None:
        self.register_tool(
            Tool(
                name="audit_content",
                description="Audit knowledge base articles for quality and staleness",
                func=self._audit_content,
            )
        )
        self.register_tool(
            Tool(
                name="find_gaps",
                description="Identify content gaps from unanswered queries",
                func=self._find_gaps,
            )
        )
        self.register_tool(
            Tool(
                name="detect_duplicates",
                description="Find duplicate or overlapping articles",
                func=self._detect_duplicates,
            )
        )
        self.register_tool(
            Tool(
                name="generate_update",
                description="Generate an updated version of an article",
                func=self._generate_update,
            )
        )
        self.register_tool(
            Tool(
                name="request_content_approval",
                description="Request human approval for content changes",
                func=self._request_content_approval,
                requires_approval=True,
            )
        )

    async def _audit_content(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        chain = self.AUDIT_PROMPT | self.llm
        result = await chain.ainvoke({"articles": json.dumps(articles[:20], indent=2)})
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {"audit_results": [], "overall_health": 50, "stale_count": 0, "action_needed_count": 0}

    async def _find_gaps(
        self, queries: List[str], existing_topics: List[str]
    ) -> Dict[str, Any]:
        chain = self.GAP_ANALYSIS_PROMPT | self.llm
        result = await chain.ainvoke({
            "queries": "\n".join(f"- {q}" for q in queries[:50]),
            "existing_topics": "\n".join(f"- {t}" for t in existing_topics[:50]),
        })
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {"gaps": [], "total_gaps": 0, "coverage_score": 50}

    async def _detect_duplicates(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        chain = self.DEDUP_PROMPT | self.llm
        result = await chain.ainvoke({"articles": json.dumps(articles[:20], indent=2)})
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {"duplicate_groups": [], "total_duplicates": 0}

    async def _generate_update(
        self, current_content: str, reason: str, context: str = ""
    ) -> Dict[str, Any]:
        chain = self.UPDATE_PROMPT | self.llm
        result = await chain.ainvoke({
            "current_content": current_content[:3000],
            "reason": reason,
            "context": context,
        })
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {"title": "", "content": result.content, "summary_of_changes": "", "tags": [], "confidence": 50}

    async def _request_content_approval(
        self, changes: List[Dict[str, Any]], summary: str
    ) -> Dict[str, Any]:
        return {
            "approval_requested": True,
            "changes_count": len(changes),
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def plan(self, state: AgentState) -> Dict[str, Any]:
        step = state.current_step

        if step == 0:
            articles = state.input_data.get("articles", [])
            return {
                "action": "audit_content",
                "action_input": {"articles": articles},
            }
        elif step == 1:
            return {
                "action": "detect_duplicates",
                "action_input": {"articles": state.input_data.get("articles", [])},
            }
        elif step == 2:
            queries = state.input_data.get("unanswered_queries", [])
            topics = [a.get("title", "") for a in state.input_data.get("articles", [])]
            return {
                "action": "find_gaps",
                "action_input": {"queries": queries, "existing_topics": topics},
            }
        elif step == 3:
            audit = state.intermediate_steps[0] if len(state.intermediate_steps) > 0 else {}
            needs_action = audit.get("action_needed_count", 0)
            if needs_action > 0:
                return {
                    "action": "request_content_approval",
                    "action_input": {
                        "changes": audit.get("audit_results", []),
                        "summary": f"{needs_action} articles need attention",
                    },
                    "requires_approval": True,
                }
            return {"action": "complete", "action_input": {}}

        return {"action": "complete", "action_input": {}}

    async def execute_step(self, state: AgentState, action: Dict[str, Any]) -> Dict[str, Any]:
        action_name = action.get("action")
        action_input = action.get("action_input", {})

        if action_name == "audit_content":
            result = await self._audit_content(action_input.get("articles", []))
            state.output_data["audit"] = result
            return {"action": action_name, **result}
        elif action_name == "detect_duplicates":
            result = await self._detect_duplicates(action_input.get("articles", []))
            state.output_data["duplicates"] = result
            return {"action": action_name, **result}
        elif action_name == "find_gaps":
            result = await self._find_gaps(
                action_input.get("queries", []),
                action_input.get("existing_topics", []),
            )
            state.output_data["gaps"] = result
            return {"action": action_name, **result}
        elif action_name == "generate_update":
            result = await self._generate_update(**action_input)
            return {"action": action_name, **result}
        elif action_name == "request_content_approval":
            result = await self._request_content_approval(**action_input)
            await self.request_human_feedback(
                question="Knowledge base changes require approval",
                context=result,
                options=["approve_all", "approve_partial", "reject"],
            )
            return {"action": action_name, **result}
        elif action_name == "complete":
            return {"action": "complete", "completed": True}

        return {"action": action_name, "error": "Unknown action"}

    def should_continue(self, state: AgentState) -> bool:
        if state.current_step >= self.config.max_iterations:
            return False
        if state.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.AWAITING_HUMAN]:
            return False
        if state.intermediate_steps and state.intermediate_steps[-1].get("action") == "complete":
            return False
        return True


KnowledgeManagerBlueprint = AgentBlueprint(
    name="knowledge_manager",
    agent_class=KnowledgeManagerAgent,
    description="Knowledge base curation agent with auditing, gap analysis, and deduplication",
    default_config={
        "max_iterations": 5,
        "timeout_seconds": 120,
        "confidence_threshold": 0.7,
        "require_human_approval": True,
    },
    required_tools=["audit_content", "find_gaps", "detect_duplicates"],
    version="1.0.0",
)
