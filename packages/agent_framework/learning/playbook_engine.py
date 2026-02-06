"""
Playbook Engine for auto-generated resolution workflows.

Derives playbooks from successful resolution traces in the Activity Graph,
compiles them into executable workflows, and suggests them to agents before
they plan from scratch.

Optionally uses LangGraph (MIT) for compiling playbooks into state-machine
workflows. Falls back to simple sequential execution when LangGraph is
not installed.

No hard dependency on LangGraph — gracefully degrades.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from .playbook_models import (
    Playbook,
    PlaybookEdge,
    PlaybookStatus,
    PlaybookStep,
    PlaybookSuggestion,
    StepType,
)

logger = logging.getLogger(__name__)

_LANGGRAPH_AVAILABLE = False

try:
    from langgraph.graph import END, StateGraph

    _LANGGRAPH_AVAILABLE = True
except ImportError:
    logger.debug("langgraph not installed; PlaybookEngine will use sequential fallback")


class PlaybookEngine:
    """
    Manages playbook lifecycle: extraction, compilation, suggestion, execution.

    Usage::

        engine = PlaybookEngine(activity_graph=graph, llm=llm)
        await engine.initialize()

        # Suggest a playbook for a new ticket
        suggestions = await engine.suggest("billing", tenant_id="acme")

        # Execute a playbook
        result = await engine.execute(playbook, agent, input_data)

        # Extract new playbooks from graph patterns
        new_playbooks = await engine.extract_playbooks("billing", tenant_id="acme")
    """

    DEFAULT_MIN_SAMPLES = 3
    DEFAULT_MIN_SUCCESS_RATE = 0.7

    def __init__(
        self,
        activity_graph: Optional[Any] = None,
        llm: Optional[Any] = None,
        min_samples: Optional[int] = None,
        min_success_rate: Optional[float] = None,
    ) -> None:
        self._graph = activity_graph
        self._llm = llm
        self._min_samples = min_samples or int(
            os.getenv("PLAYBOOK_MIN_SAMPLES", str(self.DEFAULT_MIN_SAMPLES))
        )
        self._min_success_rate = min_success_rate or float(
            os.getenv("PLAYBOOK_MIN_SUCCESS_RATE", str(self.DEFAULT_MIN_SUCCESS_RATE))
        )
        self._playbooks: Dict[str, Playbook] = {}
        self._initialized = False

    @property
    def available(self) -> bool:
        return self._initialized

    @property
    def using_langgraph(self) -> bool:
        return _LANGGRAPH_AVAILABLE

    async def initialize(self) -> None:
        """Initialize the playbook engine."""
        if self._initialized:
            return

        if self._llm is None:
            try:
                from langchain_openai import ChatOpenAI

                self._llm = ChatOpenAI(temperature=0.2)
            except Exception:
                logger.debug("PlaybookEngine: LLM not available, extraction disabled")

        self._initialized = True
        logger.info(
            "PlaybookEngine: initialized (langgraph=%s, llm=%s)",
            _LANGGRAPH_AVAILABLE,
            self._llm is not None,
        )

    # ── Playbook Suggestion ───────────────────────────────────

    async def suggest(
        self,
        category: str,
        tenant_id: str = "",
        priority: str = "",
        top_k: int = 3,
    ) -> List[PlaybookSuggestion]:
        """
        Suggest playbooks for a given category/context.

        Returns ranked list of PlaybookSuggestions.
        """
        candidates = []
        for pb in self._playbooks.values():
            if pb.status != PlaybookStatus.ACTIVE:
                continue
            if pb.category != category:
                continue
            if tenant_id and pb.tenant_id and pb.tenant_id != tenant_id:
                continue
            if pb.computed_success_rate < self._min_success_rate:
                continue

            relevance = pb.computed_success_rate * 0.6 + min(pb.sample_count / 20, 1.0) * 0.4
            candidates.append(
                PlaybookSuggestion(
                    playbook=pb,
                    relevance_score=round(relevance, 3),
                    reason=f"Success rate {pb.computed_success_rate:.0%} across {pb.sample_count} samples",
                )
            )

        candidates.sort(key=lambda s: s.relevance_score, reverse=True)
        return candidates[:top_k]

    # ── Playbook Extraction ───────────────────────────────────

    async def extract_playbooks(
        self,
        category: str,
        tenant_id: str = "",
    ) -> List[Playbook]:
        """
        Extract new playbooks from successful resolution patterns in the graph.

        Queries the Activity Graph for resolution clusters, then uses the LLM
        to summarize common step sequences into playbook definitions.
        """
        if self._graph is None:
            return []

        candidates = await self._graph.get_playbook_candidates(
            category=category,
            tenant_id=tenant_id,
            min_count=self._min_samples,
        )

        new_playbooks = []
        for candidate in candidates:
            blueprint = candidate.get("blueprint", "unknown")
            resolutions = candidate.get("resolutions", [])

            if isinstance(resolutions, list) and len(resolutions) >= self._min_samples:
                pb = await self._build_playbook_from_resolutions(
                    blueprint=blueprint,
                    category=category,
                    resolutions=resolutions,
                    tenant_id=tenant_id,
                )
                if pb:
                    self._playbooks[pb.id] = pb
                    new_playbooks.append(pb)

        return new_playbooks

    async def _build_playbook_from_resolutions(
        self,
        blueprint: str,
        category: str,
        resolutions: List[Dict[str, Any]],
        tenant_id: str = "",
    ) -> Optional[Playbook]:
        """Build a playbook from a cluster of similar resolutions."""
        # Extract common step sequences
        all_steps: List[List[str]] = []
        resolution_ids: List[str] = []
        for res in resolutions:
            steps_str = res.get("steps", "")
            if isinstance(steps_str, str) and steps_str:
                all_steps.append(steps_str.split(","))
            elif isinstance(steps_str, list):
                all_steps.append(steps_str)
            res_id = res.get("id", "")
            if res_id:
                resolution_ids.append(res_id)

        if not all_steps:
            return None

        # Find the most common step sequence
        step_sequences = [tuple(s) for s in all_steps]
        from collections import Counter

        most_common_seq = Counter(step_sequences).most_common(1)
        if not most_common_seq:
            return None

        common_steps = list(most_common_seq[0][0])

        # Use LLM to generate playbook description if available
        description = f"Auto-generated playbook for {category} issues using {blueprint} agent"
        if self._llm is not None:
            try:
                from langchain_core.prompts import ChatPromptTemplate

                prompt = ChatPromptTemplate.from_template(
                    "Given these resolution steps for {category} support issues:\n"
                    "Steps: {steps}\n"
                    "Number of successful resolutions: {count}\n\n"
                    "Write a brief 1-2 sentence description of this playbook. "
                    "Be specific about what it does."
                )
                chain = prompt | self._llm
                result = await chain.ainvoke({
                    "category": category,
                    "steps": " → ".join(common_steps),
                    "count": len(resolutions),
                })
                description = result.content.strip()
            except Exception as e:
                logger.debug("PlaybookEngine: LLM description generation failed: %s", e)

        # Build playbook steps
        pb_steps = []
        pb_edges = []
        prev_step_id = None

        for i, step_name in enumerate(common_steps):
            step = PlaybookStep(
                name=step_name,
                description=f"Execute {step_name}",
                step_type=StepType.TOOL_CALL,
                tool_name=step_name,
            )
            pb_steps.append(step)

            if prev_step_id:
                pb_edges.append(PlaybookEdge(
                    from_step_id=prev_step_id,
                    to_step_id=step.id,
                    label=f"step_{i}",
                ))
            prev_step_id = step.id

        # Calculate success rate from resolutions
        success_count = sum(1 for r in resolutions if r.get("success", False))
        total = len(resolutions)

        playbook = Playbook(
            name=f"{category.title()} Resolution ({blueprint})",
            description=description,
            category=category,
            agent_blueprint=blueprint,
            status=PlaybookStatus.ACTIVE,
            steps=pb_steps,
            edges=pb_edges,
            entry_step_id=pb_steps[0].id if pb_steps else "",
            success_rate=success_count / total if total > 0 else 0.0,
            success_count=success_count,
            sample_count=total,
            created_from=resolution_ids,
            tenant_id=tenant_id,
        )

        logger.info(
            "PlaybookEngine: created playbook '%s' (steps=%d, success_rate=%.2f)",
            playbook.name,
            len(pb_steps),
            playbook.success_rate,
        )
        return playbook

    # ── Playbook Execution ────────────────────────────────────

    async def execute(
        self,
        playbook: Playbook,
        agent: Any,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a playbook using an agent.

        If LangGraph is available, compiles the playbook into a StateGraph.
        Otherwise, executes steps sequentially.
        """
        playbook.execution_count += 1

        if _LANGGRAPH_AVAILABLE:
            return await self._execute_with_langgraph(playbook, agent, input_data)
        else:
            return await self._execute_sequential(playbook, agent, input_data)

    async def _execute_with_langgraph(
        self,
        playbook: Playbook,
        agent: Any,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute playbook using LangGraph StateGraph."""
        from typing import TypedDict

        class PlaybookState(TypedDict):
            input_data: Dict[str, Any]
            step_results: Dict[str, Any]
            current_step: str
            completed: bool
            error: Optional[str]

        builder = StateGraph(PlaybookState)

        # Add a node for each step
        for step in playbook.steps:
            step_name = step.id

            async def _make_step_fn(s: PlaybookStep):
                async def step_fn(state: PlaybookState) -> PlaybookState:
                    try:
                        tool = agent.get_tool(s.tool_name)
                        if tool and tool.func:
                            result = await tool.func(**state["input_data"])
                        else:
                            result = {"skipped": True, "reason": f"Tool {s.tool_name} not found"}
                        state["step_results"][s.id] = result
                        state["current_step"] = s.id
                    except Exception as e:
                        state["step_results"][s.id] = {"error": str(e)}
                        state["error"] = str(e)
                    return state
                return step_fn

            node_fn = await _make_step_fn(step)
            builder.add_node(step_name, node_fn)

        # Add edges
        if playbook.entry_step_id:
            builder.set_entry_point(playbook.entry_step_id)

        for edge in playbook.edges:
            if edge.condition:
                builder.add_conditional_edges(
                    edge.from_step_id,
                    lambda state, cond=edge.condition: edge.to_step_id if state.get("error") is None else END,
                )
            else:
                builder.add_edge(edge.from_step_id, edge.to_step_id)

        # Set finish point (last step → END)
        if playbook.steps:
            last_step = playbook.steps[-1]
            has_outgoing = any(e.from_step_id == last_step.id for e in playbook.edges)
            if not has_outgoing:
                builder.add_edge(last_step.id, END)

        # Compile and run
        try:
            graph = builder.compile()
            initial_state: PlaybookState = {
                "input_data": input_data,
                "step_results": {},
                "current_step": "",
                "completed": False,
                "error": None,
            }
            final_state = await graph.ainvoke(initial_state)
            success = final_state.get("error") is None
            playbook.record_execution(success)

            return {
                "playbook_id": playbook.id,
                "success": success,
                "step_results": final_state.get("step_results", {}),
                "error": final_state.get("error"),
                "engine": "langgraph",
            }
        except Exception as e:
            playbook.record_execution(False)
            return {
                "playbook_id": playbook.id,
                "success": False,
                "error": str(e),
                "engine": "langgraph",
            }

    async def _execute_sequential(
        self,
        playbook: Playbook,
        agent: Any,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute playbook steps sequentially (fallback when LangGraph unavailable)."""
        step_results: Dict[str, Any] = {}
        error: Optional[str] = None

        current_step_id = playbook.entry_step_id
        visited = set()

        while current_step_id and current_step_id not in visited:
            visited.add(current_step_id)
            step = playbook.get_step(current_step_id)
            if step is None:
                break

            try:
                tool = agent.get_tool(step.tool_name) if hasattr(agent, "get_tool") else None
                if tool and tool.func:
                    result = await tool.func(**input_data)
                else:
                    result = {"skipped": True, "reason": f"Tool {step.tool_name} not found"}
                step_results[step.id] = result
            except Exception as e:
                step_results[step.id] = {"error": str(e)}
                error = str(e)
                break

            # Find next step
            next_steps = playbook.get_next_steps(current_step_id)
            current_step_id = next_steps[0].id if next_steps else None

        success = error is None
        playbook.record_execution(success)

        return {
            "playbook_id": playbook.id,
            "success": success,
            "step_results": step_results,
            "error": error,
            "engine": "sequential",
        }

    # ── Playbook Management ───────────────────────────────────

    def register_playbook(self, playbook: Playbook) -> None:
        """Register a playbook (manually or from extraction)."""
        self._playbooks[playbook.id] = playbook

    def get_playbook(self, playbook_id: str) -> Optional[Playbook]:
        """Get a playbook by ID."""
        return self._playbooks.get(playbook_id)

    def list_playbooks(
        self,
        category: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[PlaybookStatus] = None,
    ) -> List[Playbook]:
        """List playbooks with optional filters."""
        results = list(self._playbooks.values())
        if category:
            results = [pb for pb in results if pb.category == category]
        if tenant_id:
            results = [pb for pb in results if pb.tenant_id == tenant_id]
        if status:
            results = [pb for pb in results if pb.status == status]
        return results

    def deprecate_playbook(self, playbook_id: str) -> bool:
        """Mark a playbook as deprecated."""
        pb = self._playbooks.get(playbook_id)
        if pb:
            pb.status = PlaybookStatus.DEPRECATED
            pb.updated_at = datetime.utcnow().isoformat()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get playbook engine statistics."""
        active = [pb for pb in self._playbooks.values() if pb.status == PlaybookStatus.ACTIVE]
        total_executions = sum(pb.execution_count for pb in self._playbooks.values())
        total_successes = sum(pb.success_count for pb in self._playbooks.values())

        return {
            "total_playbooks": len(self._playbooks),
            "active_playbooks": len(active),
            "total_executions": total_executions,
            "total_successes": total_successes,
            "overall_success_rate": (
                total_successes / total_executions if total_executions > 0 else 0.0
            ),
            "langgraph_available": _LANGGRAPH_AVAILABLE,
            "categories": list(set(pb.category for pb in active)),
        }
