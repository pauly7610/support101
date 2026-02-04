"""
Triage Agent Blueprint - Intelligent ticket routing and prioritization.

Analyzes incoming tickets and routes them to appropriate agents or queues
based on content, urgency, and available resources.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..core.base_agent import AgentConfig, AgentState, AgentStatus, BaseAgent, Tool
from ..core.agent_registry import AgentBlueprint


class TriageAgent(BaseAgent):
    """
    Intelligent ticket triage agent.
    
    Workflow:
    1. Analyze ticket content and metadata
    2. Classify priority and category
    3. Identify required skills/expertise
    4. Route to appropriate queue or agent
    """
    
    TRIAGE_PROMPT = ChatPromptTemplate.from_template(
        "You are a ticket triage specialist. Analyze the following support ticket.\n\n"
        "Ticket Content: {content}\n"
        "Customer Tier: {customer_tier}\n"
        "Previous Tickets: {ticket_history}\n\n"
        "Provide analysis in JSON format:\n"
        "{{\n"
        '  "priority": "critical|high|medium|low",\n'
        '  "category": "billing|technical|account|product|general|complaint",\n'
        '  "sentiment": "positive|neutral|negative|angry",\n'
        '  "required_skills": ["skill1", "skill2"],\n'
        '  "estimated_complexity": "simple|moderate|complex",\n'
        '  "suggested_queue": "queue_name",\n'
        '  "auto_resolvable": true|false,\n'
        '  "reasoning": "brief explanation"\n'
        "}}"
    )
    
    ROUTING_RULES = {
        "critical": {"max_wait_minutes": 5, "escalate_after": 15},
        "high": {"max_wait_minutes": 15, "escalate_after": 60},
        "medium": {"max_wait_minutes": 60, "escalate_after": 240},
        "low": {"max_wait_minutes": 240, "escalate_after": 1440},
    }
    
    def __init__(self, config: AgentConfig) -> None:
        super().__init__(config)
        self.llm = ChatOpenAI(temperature=0.1)
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register triage-specific tools."""
        self.register_tool(Tool(
            name="analyze_ticket",
            description="Analyze ticket content for triage",
            func=self._analyze_ticket,
        ))
        self.register_tool(Tool(
            name="check_customer_history",
            description="Check customer's ticket history",
            func=self._check_customer_history,
        ))
        self.register_tool(Tool(
            name="assign_to_queue",
            description="Assign ticket to a queue",
            func=self._assign_to_queue,
        ))
        self.register_tool(Tool(
            name="assign_to_agent",
            description="Assign ticket to a specific agent",
            func=self._assign_to_agent,
            requires_approval=True,
        ))
    
    async def _analyze_ticket(
        self,
        content: str,
        customer_tier: str = "standard",
        ticket_history: str = "None",
    ) -> Dict[str, Any]:
        """Analyze ticket using LLM."""
        chain = self.TRIAGE_PROMPT | self.llm
        result = await chain.ainvoke({
            "content": content,
            "customer_tier": customer_tier,
            "ticket_history": ticket_history,
        })
        
        import json
        try:
            analysis = json.loads(result.content)
        except json.JSONDecodeError:
            analysis = {
                "priority": "medium",
                "category": "general",
                "sentiment": "neutral",
                "required_skills": [],
                "estimated_complexity": "moderate",
                "suggested_queue": "general_support",
                "auto_resolvable": False,
                "reasoning": "Failed to parse LLM response",
            }
        
        return analysis
    
    async def _check_customer_history(
        self, customer_id: str
    ) -> Dict[str, Any]:
        """Check customer's ticket history (stub - integrate with your DB)."""
        return {
            "customer_id": customer_id,
            "total_tickets": 0,
            "open_tickets": 0,
            "avg_satisfaction": None,
            "is_vip": False,
            "notes": [],
        }
    
    async def _assign_to_queue(
        self,
        ticket_id: str,
        queue_name: str,
        priority: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Assign ticket to a queue."""
        routing_rules = self.ROUTING_RULES.get(priority, self.ROUTING_RULES["medium"])
        
        return {
            "assigned": True,
            "ticket_id": ticket_id,
            "queue": queue_name,
            "priority": priority,
            "max_wait_minutes": routing_rules["max_wait_minutes"],
            "escalate_after_minutes": routing_rules["escalate_after"],
            "assigned_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
    
    async def _assign_to_agent(
        self,
        ticket_id: str,
        agent_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Assign ticket directly to an agent."""
        return {
            "assigned": True,
            "ticket_id": ticket_id,
            "agent_id": agent_id,
            "reason": reason,
            "assigned_at": datetime.utcnow().isoformat(),
        }
    
    async def plan(self, state: AgentState) -> Dict[str, Any]:
        """Determine next triage action."""
        step = state.current_step
        
        if step == 0:
            return {
                "action": "check_customer_history",
                "action_input": {
                    "customer_id": state.input_data.get("customer_id", "unknown"),
                },
            }
        elif step == 1:
            customer_history = state.intermediate_steps[-1] if state.intermediate_steps else {}
            return {
                "action": "analyze_ticket",
                "action_input": {
                    "content": state.input_data.get("content", ""),
                    "customer_tier": "vip" if customer_history.get("is_vip") else "standard",
                    "ticket_history": str(customer_history.get("total_tickets", 0)) + " previous tickets",
                },
            }
        elif step == 2:
            analysis = state.intermediate_steps[-1] if state.intermediate_steps else {}
            
            if analysis.get("priority") == "critical" or analysis.get("sentiment") == "angry":
                return {
                    "action": "request_human_review",
                    "action_input": {
                        "reason": "Critical priority or angry customer",
                        "analysis": analysis,
                    },
                    "requires_approval": True,
                }
            
            return {
                "action": "assign_to_queue",
                "action_input": {
                    "ticket_id": state.input_data.get("ticket_id", "unknown"),
                    "queue_name": analysis.get("suggested_queue", "general_support"),
                    "priority": analysis.get("priority", "medium"),
                    "metadata": {
                        "category": analysis.get("category"),
                        "required_skills": analysis.get("required_skills", []),
                        "auto_resolvable": analysis.get("auto_resolvable", False),
                    },
                },
            }
        
        return {"action": "complete", "action_input": {}}
    
    async def execute_step(
        self, state: AgentState, action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a triage step."""
        action_name = action.get("action")
        action_input = action.get("action_input", {})
        
        if action_name == "check_customer_history":
            result = await self._check_customer_history(action_input["customer_id"])
            return {"action": action_name, **result}
        
        elif action_name == "analyze_ticket":
            result = await self._analyze_ticket(
                action_input["content"],
                action_input.get("customer_tier", "standard"),
                action_input.get("ticket_history", "None"),
            )
            return {"action": action_name, **result}
        
        elif action_name == "assign_to_queue":
            result = await self._assign_to_queue(
                action_input["ticket_id"],
                action_input["queue_name"],
                action_input["priority"],
                action_input.get("metadata"),
            )
            state.output_data["assignment"] = result
            return {"action": action_name, **result}
        
        elif action_name == "request_human_review":
            await self.request_human_feedback(
                question="Review critical ticket triage decision",
                context=action_input,
                options=["approve_routing", "escalate_immediately", "reassign"],
            )
            return {"action": action_name, "awaiting_human": True}
        
        elif action_name == "complete":
            return {"action": "complete", "completed": True}
        
        return {"action": action_name, "error": "Unknown action"}
    
    def should_continue(self, state: AgentState) -> bool:
        """Check if triage should continue."""
        if state.current_step >= self.config.max_iterations:
            return False
        if state.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.AWAITING_HUMAN]:
            return False
        if state.intermediate_steps and state.intermediate_steps[-1].get("action") == "complete":
            return False
        if state.output_data.get("assignment"):
            return False
        return True


TriageAgentBlueprint = AgentBlueprint(
    name="triage_agent",
    agent_class=TriageAgent,
    description="Intelligent ticket routing and prioritization agent",
    default_config={
        "max_iterations": 4,
        "timeout_seconds": 30,
        "require_human_approval": False,
    },
    required_tools=["analyze_ticket", "assign_to_queue"],
    version="1.0.0",
)
