"""
Configuration schema and validation utilities.

Provides Pydantic-based configuration validation.
"""

from typing import Any, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T", bound=BaseModel)


class ConfigSchema(BaseModel):
    """Base schema for agent configuration validation."""

    max_iterations: int = Field(default=10, ge=1, le=100)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    require_human_approval: bool = Field(default=False)
    allowed_tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class SupportAgentConfigSchema(ConfigSchema):
    """Schema for SupportAgent configuration."""

    knowledge_base_top_k: int = Field(default=5, ge=1, le=20)
    include_sources: bool = Field(default=True)
    max_response_length: int = Field(default=2000, ge=100, le=10000)
    escalation_keywords: list[str] = Field(default_factory=list)

    @field_validator("escalation_keywords")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        return [kw.lower().strip() for kw in v if kw.strip()]


class TriageAgentConfigSchema(ConfigSchema):
    """Schema for TriageAgent configuration."""

    auto_assign: bool = Field(default=True)
    priority_boost_vip: bool = Field(default=True)
    sentiment_analysis: bool = Field(default=True)
    default_queue: str = Field(default="general_support")

    @field_validator("default_queue")
    @classmethod
    def validate_queue(cls, v: str) -> str:
        if not v or not v.strip():
            return "general_support"
        return v.strip().lower().replace(" ", "_")


class TenantConfigSchema(BaseModel):
    """Schema for tenant configuration."""

    name: str = Field(..., min_length=1, max_length=100)
    tier: str = Field(default="starter")
    allowed_blueprints: list[str] = Field(default_factory=list)
    webhook_url: str | None = Field(default=None)
    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        valid_tiers = {"free", "starter", "professional", "enterprise"}
        if v.lower() not in valid_tiers:
            raise ValueError(f"Invalid tier. Must be one of: {valid_tiers}")
        return v.lower()

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v


class HITLRequestConfigSchema(BaseModel):
    """Schema for HITL request configuration."""

    priority: str = Field(default="medium")
    expires_in_hours: int | None = Field(default=None, ge=1, le=168)
    auto_assign: bool = Field(default=True)
    notify_channels: list[str] = Field(default_factory=list)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        valid = {"critical", "high", "medium", "low"}
        if v.lower() not in valid:
            raise ValueError(f"Invalid priority. Must be one of: {valid}")
        return v.lower()


class EscalationRuleConfigSchema(BaseModel):
    """Schema for escalation rule configuration."""

    name: str = Field(..., min_length=1, max_length=100)
    trigger: str
    target_level: str = Field(default="l2")
    priority: str = Field(default="medium")
    conditions: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = Field(default=True)

    @field_validator("trigger")
    @classmethod
    def validate_trigger(cls, v: str) -> str:
        valid = {
            "low_confidence",
            "negative_sentiment",
            "timeout",
            "explicit_request",
            "repeated_failure",
            "high_value_customer",
            "sensitive_topic",
            "policy_violation",
            "manual",
        }
        if v.lower() not in valid:
            raise ValueError(f"Invalid trigger. Must be one of: {valid}")
        return v.lower()

    @field_validator("target_level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid = {"l1", "l2", "l3", "manager", "executive"}
        if v.lower() not in valid:
            raise ValueError(f"Invalid level. Must be one of: {valid}")
        return v.lower()


def validate_config(
    config: dict[str, Any],
    schema: type[T],
) -> T:
    """
    Validate configuration against a schema.

    Args:
        config: Configuration dictionary
        schema: Pydantic model class to validate against

    Returns:
        Validated configuration as schema instance

    Raises:
        ValidationError: If validation fails
    """
    return schema.model_validate(config)


def validate_config_dict(
    config: dict[str, Any],
    schema: type[BaseModel],
) -> dict[str, Any]:
    """
    Validate and return configuration as dictionary.

    Args:
        config: Configuration dictionary
        schema: Pydantic model class to validate against

    Returns:
        Validated configuration as dictionary
    """
    validated = schema.model_validate(config)
    return validated.model_dump()


def get_schema_for_blueprint(blueprint_name: str) -> type[ConfigSchema]:
    """Get the appropriate config schema for a blueprint."""
    schemas = {
        "support_agent": SupportAgentConfigSchema,
        "triage_agent": TriageAgentConfigSchema,
    }
    return schemas.get(blueprint_name, ConfigSchema)
