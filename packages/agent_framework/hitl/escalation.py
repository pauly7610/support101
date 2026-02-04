"""
Escalation Management System.

Provides configurable escalation policies and rules for:
- Automatic escalation based on conditions
- Time-based escalation
- Confidence-based escalation
- Sentiment-based escalation
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from .queue import HITLPriority, HITLQueue, HITLRequestType


class EscalationTrigger(str, Enum):
    """Types of escalation triggers."""

    LOW_CONFIDENCE = "low_confidence"
    NEGATIVE_SENTIMENT = "negative_sentiment"
    TIMEOUT = "timeout"
    EXPLICIT_REQUEST = "explicit_request"
    REPEATED_FAILURE = "repeated_failure"
    HIGH_VALUE_CUSTOMER = "high_value_customer"
    SENSITIVE_TOPIC = "sensitive_topic"
    POLICY_VIOLATION = "policy_violation"
    MANUAL = "manual"


class EscalationLevel(str, Enum):
    """Escalation severity levels."""

    L1 = "l1"  # First-line support
    L2 = "l2"  # Specialized support
    L3 = "l3"  # Expert/Engineering
    MANAGER = "manager"
    EXECUTIVE = "executive"


@dataclass
class EscalationRule:
    """A rule that triggers escalation."""

    rule_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    trigger: EscalationTrigger = EscalationTrigger.MANUAL
    target_level: EscalationLevel = EscalationLevel.L2
    priority: HITLPriority = HITLPriority.MEDIUM

    conditions: Dict[str, Any] = field(default_factory=dict)

    enabled: bool = True
    tenant_ids: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if context matches rule conditions."""
        if not self.enabled:
            return False

        for key, expected in self.conditions.items():
            actual = context.get(key)

            if isinstance(expected, dict):
                if "min" in expected and actual < expected["min"]:
                    return False
                if "max" in expected and actual > expected["max"]:
                    return False
                if "in" in expected and actual not in expected["in"]:
                    return False
                if "not_in" in expected and actual in expected["not_in"]:
                    return False
            elif actual != expected:
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger.value,
            "target_level": self.target_level.value,
            "priority": self.priority.value,
            "conditions": self.conditions,
            "enabled": self.enabled,
            "tenant_ids": self.tenant_ids,
        }


@dataclass
class EscalationPolicy:
    """A collection of escalation rules for a tenant."""

    policy_id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: str = ""
    name: str = ""
    description: str = ""

    rules: List[EscalationRule] = field(default_factory=list)

    default_level: EscalationLevel = EscalationLevel.L1
    auto_escalate_after: Optional[timedelta] = None

    notification_channels: List[str] = field(default_factory=list)

    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_rule(self, rule: EscalationRule) -> None:
        """Add a rule to the policy."""
        self.rules.append(rule)
        self.updated_at = datetime.utcnow()

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the policy."""
        original_len = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        if len(self.rules) < original_len:
            self.updated_at = datetime.utcnow()
            return True
        return False

    def evaluate(self, context: Dict[str, Any]) -> Optional[EscalationRule]:
        """
        Evaluate context against all rules.

        Returns the first matching rule, or None if no match.
        """
        if not self.enabled:
            return None

        for rule in self.rules:
            if rule.matches(context):
                return rule

        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "rules": [r.to_dict() for r in self.rules],
            "default_level": self.default_level.value,
            "auto_escalate_after_seconds": (
                self.auto_escalate_after.total_seconds() if self.auto_escalate_after else None
            ),
            "notification_channels": self.notification_channels,
            "enabled": self.enabled,
        }


class EscalationManager:
    """
    Manages escalation policies and triggers escalations.

    Integrates with HITLQueue for human review requests.
    """

    def __init__(self, hitl_queue: HITLQueue) -> None:
        self.hitl_queue = hitl_queue
        self._policies: Dict[str, EscalationPolicy] = {}
        self._tenant_policies: Dict[str, str] = {}
        self._escalation_handlers: Dict[EscalationLevel, List[Callable]] = {}
        self._notification_handlers: List[Callable] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self) -> None:
        """Create default escalation rules."""
        self._default_rules = [
            EscalationRule(
                name="Low Confidence Response",
                description="Escalate when agent confidence is below threshold",
                trigger=EscalationTrigger.LOW_CONFIDENCE,
                target_level=EscalationLevel.L2,
                priority=HITLPriority.MEDIUM,
                conditions={"confidence": {"max": 0.75}},
            ),
            EscalationRule(
                name="Angry Customer",
                description="Escalate when customer sentiment is negative",
                trigger=EscalationTrigger.NEGATIVE_SENTIMENT,
                target_level=EscalationLevel.L2,
                priority=HITLPriority.HIGH,
                conditions={"sentiment": {"in": ["angry", "frustrated", "negative"]}},
            ),
            EscalationRule(
                name="VIP Customer",
                description="Escalate for high-value customers",
                trigger=EscalationTrigger.HIGH_VALUE_CUSTOMER,
                target_level=EscalationLevel.L2,
                priority=HITLPriority.HIGH,
                conditions={"is_vip": True},
            ),
            EscalationRule(
                name="Repeated Failures",
                description="Escalate after multiple failed attempts",
                trigger=EscalationTrigger.REPEATED_FAILURE,
                target_level=EscalationLevel.L3,
                priority=HITLPriority.HIGH,
                conditions={"failure_count": {"min": 3}},
            ),
            EscalationRule(
                name="Sensitive Topic",
                description="Escalate for sensitive topics requiring human review",
                trigger=EscalationTrigger.SENSITIVE_TOPIC,
                target_level=EscalationLevel.MANAGER,
                priority=HITLPriority.CRITICAL,
                conditions={"topic": {"in": ["legal", "security", "privacy", "complaint"]}},
            ),
        ]

    def create_policy(
        self,
        tenant_id: str,
        name: str,
        description: str = "",
        include_default_rules: bool = True,
    ) -> EscalationPolicy:
        """Create a new escalation policy for a tenant."""
        policy = EscalationPolicy(
            tenant_id=tenant_id,
            name=name,
            description=description,
        )

        if include_default_rules:
            for rule in self._default_rules:
                policy.add_rule(
                    EscalationRule(
                        name=rule.name,
                        description=rule.description,
                        trigger=rule.trigger,
                        target_level=rule.target_level,
                        priority=rule.priority,
                        conditions=rule.conditions.copy(),
                    )
                )

        self._policies[policy.policy_id] = policy
        self._tenant_policies[tenant_id] = policy.policy_id

        return policy

    def get_policy(self, policy_id: str) -> Optional[EscalationPolicy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def get_tenant_policy(self, tenant_id: str) -> Optional[EscalationPolicy]:
        """Get the policy for a tenant."""
        policy_id = self._tenant_policies.get(tenant_id)
        if policy_id:
            return self._policies.get(policy_id)
        return None

    def register_handler(
        self,
        level: EscalationLevel,
        handler: Callable,
    ) -> None:
        """Register a handler for escalations at a specific level."""
        if level not in self._escalation_handlers:
            self._escalation_handlers[level] = []
        self._escalation_handlers[level].append(handler)

    def register_notification_handler(self, handler: Callable) -> None:
        """Register a notification handler."""
        self._notification_handlers.append(handler)

    async def _notify(
        self,
        escalation: Dict[str, Any],
        channels: List[str],
    ) -> None:
        """Send notifications through registered handlers."""
        for handler in self._notification_handlers:
            try:
                result = handler(escalation, channels)
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                print(f"Notification handler error: {e}")

    async def evaluate_and_escalate(
        self,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate context against tenant policy and trigger escalation if needed.

        Args:
            agent_id: ID of the agent
            tenant_id: Tenant ID
            execution_id: Current execution ID
            context: Context to evaluate (confidence, sentiment, etc.)

        Returns:
            Escalation details if triggered, None otherwise
        """
        policy = self.get_tenant_policy(tenant_id)
        if not policy:
            return None

        matching_rule = policy.evaluate(context)
        if not matching_rule:
            return None

        return await self.trigger_escalation(
            agent_id=agent_id,
            tenant_id=tenant_id,
            execution_id=execution_id,
            rule=matching_rule,
            context=context,
        )

    async def trigger_escalation(
        self,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
        rule: EscalationRule,
        context: Dict[str, Any],
        manual_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trigger an escalation.

        Creates a HITL request and notifies handlers.
        """
        escalation = {
            "escalation_id": str(uuid4()),
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "rule": rule.to_dict() if rule else None,
            "trigger": rule.trigger.value if rule else EscalationTrigger.MANUAL.value,
            "level": rule.target_level.value if rule else EscalationLevel.L2.value,
            "priority": rule.priority.value if rule else HITLPriority.MEDIUM.value,
            "context": context,
            "manual_reason": manual_reason,
            "created_at": datetime.utcnow().isoformat(),
        }

        hitl_request = await self.hitl_queue.enqueue(
            request_type=HITLRequestType.ESCALATION,
            agent_id=agent_id,
            tenant_id=tenant_id,
            execution_id=execution_id,
            title=f"Escalation: {rule.name if rule else 'Manual'}",
            description=rule.description if rule else manual_reason or "Manual escalation",
            priority=rule.priority if rule else HITLPriority.MEDIUM,
            context=context,
            metadata={"escalation": escalation},
        )

        escalation["hitl_request_id"] = hitl_request.request_id

        level = rule.target_level if rule else EscalationLevel.L2
        handlers = self._escalation_handlers.get(level, [])
        for handler in handlers:
            try:
                result = handler(escalation)
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                print(f"Escalation handler error: {e}")

        policy = self.get_tenant_policy(tenant_id)
        if policy and policy.notification_channels:
            await self._notify(escalation, policy.notification_channels)

        return escalation

    async def manual_escalate(
        self,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
        reason: str,
        level: EscalationLevel = EscalationLevel.L2,
        priority: HITLPriority = HITLPriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Manually trigger an escalation."""
        rule = EscalationRule(
            name="Manual Escalation",
            description=reason,
            trigger=EscalationTrigger.MANUAL,
            target_level=level,
            priority=priority,
        )

        return await self.trigger_escalation(
            agent_id=agent_id,
            tenant_id=tenant_id,
            execution_id=execution_id,
            rule=rule,
            context=context or {},
            manual_reason=reason,
        )

    def get_escalation_stats(
        self,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get escalation statistics from HITL queue."""
        stats = self.hitl_queue.get_queue_stats(tenant_id)

        return {
            "total_escalations": stats["total_requests"],
            "pending_escalations": stats["pending"],
            "by_priority": stats["by_priority"],
            "avg_resolution_time_seconds": stats["avg_response_time_seconds"],
            "sla_breached": stats["sla_breached"],
        }
