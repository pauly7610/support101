"""
Playbook data models for the Playbook Engine.

A Playbook is an auto-generated resolution workflow derived from
successful traces in the Activity Graph. It encodes proven step
sequences that agents can follow instead of planning from scratch.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class PlaybookStatus(str, Enum):
    """Lifecycle status of a playbook."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class StepType(str, Enum):
    """Types of playbook steps."""

    TOOL_CALL = "tool_call"
    LLM_CALL = "llm_call"
    DECISION = "decision"
    HUMAN_REVIEW = "human_review"
    PARALLEL = "parallel"
    CONDITION = "condition"


@dataclass
class PlaybookStep:
    """A single step in a playbook workflow."""

    id: str = field(default_factory=lambda: f"step-{uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    step_type: StepType = StepType.TOOL_CALL
    tool_name: str = ""
    input_template: Dict[str, Any] = field(default_factory=dict)
    expected_output_keys: List[str] = field(default_factory=list)
    timeout_seconds: int = 60
    requires_approval: bool = False
    fallback_step_id: Optional[str] = None
    condition: Optional[str] = None  # for conditional branching

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "step_type": self.step_type.value,
            "tool_name": self.tool_name,
            "input_template": self.input_template,
            "expected_output_keys": self.expected_output_keys,
            "timeout_seconds": self.timeout_seconds,
            "requires_approval": self.requires_approval,
            "fallback_step_id": self.fallback_step_id,
            "condition": self.condition,
        }


@dataclass
class PlaybookEdge:
    """A transition between playbook steps."""

    from_step_id: str = ""
    to_step_id: str = ""
    condition: Optional[str] = None
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_step_id": self.from_step_id,
            "to_step_id": self.to_step_id,
            "condition": self.condition,
            "label": self.label,
        }


@dataclass
class Playbook:
    """
    A complete resolution playbook derived from successful traces.

    Contains an ordered set of steps (as a DAG) that agents can follow
    to resolve a specific category of issues.
    """

    id: str = field(default_factory=lambda: f"pb-{uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    category: str = ""
    agent_blueprint: str = ""
    status: PlaybookStatus = PlaybookStatus.DRAFT
    steps: List[PlaybookStep] = field(default_factory=list)
    edges: List[PlaybookEdge] = field(default_factory=list)
    entry_step_id: str = ""
    success_rate: float = 0.0
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    sample_count: int = 0
    created_from: List[str] = field(default_factory=list)  # resolution IDs
    tenant_id: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def computed_success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else self.success_rate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "agent_blueprint": self.agent_blueprint,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "edges": [e.to_dict() for e in self.edges],
            "entry_step_id": self.entry_step_id,
            "success_rate": self.computed_success_rate,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "sample_count": self.sample_count,
            "created_from": self.created_from,
            "tenant_id": self.tenant_id,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def get_step(self, step_id: str) -> Optional[PlaybookStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_next_steps(self, step_id: str) -> List[PlaybookStep]:
        """Get the next steps after a given step."""
        next_ids = [e.to_step_id for e in self.edges if e.from_step_id == step_id]
        return [s for s in self.steps if s.id in next_ids]

    def record_execution(self, success: bool) -> None:
        """Record a playbook execution outcome."""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.updated_at = datetime.utcnow().isoformat()


@dataclass
class PlaybookSuggestion:
    """A suggested playbook for a given context."""

    playbook: Playbook
    relevance_score: float = 0.0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "playbook": self.playbook.to_dict(),
            "relevance_score": self.relevance_score,
            "reason": self.reason,
        }
