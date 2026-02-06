"""
Pydantic validation models for agent tool inputs.

Provides strict input validation for all agent blueprint tool methods.
Each agent's tools validate their inputs before processing.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


# ── Support Agent Models ─────────────────────────────────────────────

class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")


class EscalateToHumanInput(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000, description="Escalation reason")
    context: Dict[str, Any] = Field(default_factory=dict, description="Escalation context")


class CreateTicketInput(BaseModel):
    subject: str = Field(..., min_length=1, max_length=512, description="Ticket subject")
    description: str = Field(default="", max_length=5000, description="Ticket description")
    priority: str = Field(default="medium", description="Ticket priority")
    customer_id: Optional[str] = Field(default=None, description="Customer ID")

    @validator("priority")
    def validate_priority(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"priority must be one of {allowed}")
        return v.lower()


# ── Triage Agent Models ──────────────────────────────────────────────

class AnalyzeTicketInput(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Ticket content")
    customer_tier: str = Field(default="standard", description="Customer tier")
    ticket_history: str = Field(default="None", description="Ticket history summary")


class AssignToQueueInput(BaseModel):
    ticket_id: str = Field(..., min_length=1, description="Ticket ID")
    queue_name: str = Field(..., min_length=1, max_length=128, description="Queue name")
    priority: str = Field(default="medium", description="Priority level")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    @validator("priority")
    def validate_priority(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"priority must be one of {allowed}")
        return v.lower()


class AssignToAgentInput(BaseModel):
    ticket_id: str = Field(..., min_length=1, description="Ticket ID")
    agent_id: str = Field(..., min_length=1, description="Agent ID")
    reason: str = Field(..., min_length=1, max_length=500, description="Assignment reason")


# ── Data Analyst Agent Models ────────────────────────────────────────

class AnalyzeDataInput(BaseModel):
    data_sample: str = Field(..., min_length=1, max_length=10000, description="Data to analyze")
    description: str = Field(default="", max_length=2000, description="Data description")
    analysis_type: str = Field(default="exploratory", description="Type of analysis")

    @validator("analysis_type")
    def validate_analysis_type(cls, v: str) -> str:
        allowed = {"exploratory", "diagnostic", "predictive", "prescriptive", "comparative"}
        if v.lower() not in allowed:
            raise ValueError(f"analysis_type must be one of {allowed}")
        return v.lower()


class GenerateInsightsInput(BaseModel):
    analysis: Dict[str, Any] = Field(..., description="Analysis results to generate insights from")
    context: str = Field(default="", max_length=2000, description="Business context")


class QueryDataInput(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="Question about the data")
    data_context: str = Field(default="", max_length=5000, description="Data context")
    previous_analysis: str = Field(default="", max_length=5000, description="Previous analysis")


# ── Code Review Agent Models ─────────────────────────────────────────

class CodeReviewInput(BaseModel):
    code: str = Field(..., min_length=1, max_length=20000, description="Code to review")
    language: str = Field(default="python", description="Programming language")

    @validator("language")
    def validate_language(cls, v: str) -> str:
        allowed = {
            "python", "javascript", "typescript", "java", "go", "rust",
            "c", "cpp", "csharp", "ruby", "php", "swift", "kotlin",
        }
        if v.lower() not in allowed:
            raise ValueError(f"language must be one of {allowed}")
        return v.lower()


class BlockMergeInput(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000, description="Block reason")
    critical_findings: List[Dict[str, Any]] = Field(
        default_factory=list, description="Critical findings"
    )


# ── QA Test Agent Models ─────────────────────────────────────────────

class GenerateTestsInput(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=256, description="Agent name")
    agent_description: str = Field(default="", max_length=2000, description="Agent description")
    sample_input: str = Field(default="", max_length=5000, description="Sample input")
    sample_output: str = Field(default="", max_length=5000, description="Sample output")


class ValidateOutputInput(BaseModel):
    test_case: Dict[str, Any] = Field(..., description="Test case definition")
    agent_input: Dict[str, Any] = Field(..., description="Agent input data")
    agent_output: Dict[str, Any] = Field(..., description="Agent output to validate")
    criteria: List[str] = Field(default_factory=list, description="Validation criteria")


class CheckRegressionInput(BaseModel):
    previous_output: Dict[str, Any] = Field(..., description="Previous output")
    current_output: Dict[str, Any] = Field(..., description="Current output")
    test_case: Dict[str, Any] = Field(..., description="Test case")


# ── Knowledge Manager Agent Models ───────────────────────────────────

class AuditContentInput(BaseModel):
    articles: List[Dict[str, Any]] = Field(
        ..., min_items=1, max_items=100, description="Articles to audit"
    )


class FindGapsInput(BaseModel):
    queries: List[str] = Field(
        ..., min_items=1, max_items=200, description="Unanswered queries"
    )
    existing_topics: List[str] = Field(
        default_factory=list, max_items=200, description="Existing article topics"
    )


class DetectDuplicatesInput(BaseModel):
    articles: List[Dict[str, Any]] = Field(
        ..., min_items=2, max_items=100, description="Articles to check for duplicates"
    )


class GenerateUpdateInput(BaseModel):
    current_content: str = Field(..., min_length=1, max_length=10000, description="Current article")
    reason: str = Field(..., min_length=1, max_length=500, description="Update reason")
    context: str = Field(default="", max_length=2000, description="Additional context")


# ── Sentiment Monitor Agent Models ───────────────────────────────────

class AnalyzeSentimentInput(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Message to analyze")
    history: List[Dict[str, str]] = Field(
        default_factory=list, max_items=50, description="Conversation history"
    )


class TrackTrajectoryInput(BaseModel):
    sentiment_history: List[Dict[str, Any]] = Field(
        ..., min_items=1, max_items=100, description="Sentiment history entries"
    )


class TriggerEscalationInput(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000, description="Escalation reason")
    sentiment_data: Dict[str, Any] = Field(..., description="Sentiment data")
    urgency: str = Field(default="high", description="Urgency level")

    @validator("urgency")
    def validate_urgency(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"urgency must be one of {allowed}")
        return v.lower()


# ── Onboarding Agent Models ──────────────────────────────────────────

class AssessCustomerInput(BaseModel):
    customer_info: Dict[str, Any] = Field(..., description="Customer information")
    product: str = Field(default="Support101 Platform", max_length=256, description="Product name")


class GenerateChecklistInput(BaseModel):
    assessment: Dict[str, Any] = Field(..., description="Customer assessment results")
    product: str = Field(default="Support101 Platform", max_length=256, description="Product name")


class ProvideGuidanceInput(BaseModel):
    step_title: str = Field(..., min_length=1, max_length=256, description="Step title")
    step_description: str = Field(..., min_length=1, max_length=2000, description="Step description")
    experience_level: str = Field(default="beginner", description="Customer experience level")
    question: str = Field(default="", max_length=2000, description="Customer question")

    @validator("experience_level")
    def validate_experience_level(cls, v: str) -> str:
        allowed = {"beginner", "intermediate", "expert"}
        if v.lower() not in allowed:
            raise ValueError(f"experience_level must be one of {allowed}")
        return v.lower()


class ValidateCompletionInput(BaseModel):
    checklist: List[Dict[str, Any]] = Field(..., description="Onboarding checklist")
    completed_steps: List[str] = Field(default_factory=list, description="Completed step IDs")
    customer_profile: Dict[str, Any] = Field(default_factory=dict, description="Customer profile")


# ── Compliance Auditor Agent Models ──────────────────────────────────

class ScanPIIInput(BaseModel):
    content: str = Field(..., min_length=1, max_length=20000, description="Content to scan for PII")


class CheckPolicyInput(BaseModel):
    action: str = Field(..., min_length=1, max_length=5000, description="Agent action description")
    response: str = Field(..., min_length=1, max_length=10000, description="Agent response")
    policies: Optional[List[str]] = Field(default=None, description="Policies to check against")

    @validator("policies")
    def validate_policies(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        allowed = {"GDPR", "HIPAA", "SOC2", "CCPA", "PCI_DSS", "FINRA_4511"}
        for p in v:
            if p.upper() not in allowed:
                raise ValueError(f"Unknown policy: {p}. Allowed: {allowed}")
        return [p.upper() for p in v]


class GenerateReportInput(BaseModel):
    pii_results: Dict[str, Any] = Field(..., description="PII scan results")
    policy_results: Dict[str, Any] = Field(..., description="Policy check results")
    scope: str = Field(default="", max_length=500, description="Audit scope description")


class TriggerRemediationInput(BaseModel):
    violation_type: str = Field(..., min_length=1, max_length=256, description="Violation type")
    severity: str = Field(default="high", description="Violation severity")
    details: Dict[str, Any] = Field(default_factory=dict, description="Violation details")
    required_action: str = Field(..., min_length=1, max_length=1000, description="Required action")

    @validator("severity")
    def validate_severity(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"severity must be one of {allowed}")
        return v.lower()
