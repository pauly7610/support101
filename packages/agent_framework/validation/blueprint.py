"""
Blueprint validation for agent framework.

Ensures blueprints and configurations are valid before use.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        message = "; ".join(
            f"{e.get('field', 'unknown')}: {e.get('message', 'invalid')}" for e in errors
        )
        super().__init__(f"Validation failed: {message}")


@dataclass
class ValidationResult:
    """Result of a validation check."""

    valid: bool
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    def add_error(self, field: str, message: str, value: Any = None) -> None:
        self.valid = False
        self.errors.append(
            {
                "field": field,
                "message": message,
                "value": value,
            }
        )

    def add_warning(self, field: str, message: str, value: Any = None) -> None:
        self.warnings.append(
            {
                "field": field,
                "message": message,
                "value": value,
            }
        )

    def merge(self, other: "ValidationResult") -> None:
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def raise_if_invalid(self) -> None:
        if not self.valid:
            raise ValidationError(self.errors)


class BlueprintValidator:
    """
    Validates agent blueprints and configurations.

    Checks:
    - Required fields are present
    - Field types are correct
    - Values are within allowed ranges
    - Required tools are available
    - Custom validation rules
    """

    def __init__(self) -> None:
        self._custom_validators: dict[str, list[Callable]] = {}

    def register_validator(
        self,
        blueprint_name: str,
        validator: Callable[[dict[str, Any]], ValidationResult],
    ) -> None:
        """Register a custom validator for a blueprint."""
        if blueprint_name not in self._custom_validators:
            self._custom_validators[blueprint_name] = []
        self._custom_validators[blueprint_name].append(validator)

    def validate_blueprint(
        self,
        name: str,
        agent_class: type,
        default_config: dict[str, Any],
        required_tools: list[str],
    ) -> ValidationResult:
        """Validate a blueprint definition."""
        result = ValidationResult(valid=True)

        if not name:
            result.add_error("name", "Blueprint name is required")
        elif not name.replace("_", "").replace("-", "").isalnum():
            result.add_error("name", "Blueprint name must be alphanumeric with underscores/hyphens")

        if agent_class is None:
            result.add_error("agent_class", "Agent class is required")
        else:
            required_methods = ["plan", "execute_step", "should_continue"]
            for method in required_methods:
                if not hasattr(agent_class, method):
                    result.add_error(
                        "agent_class",
                        f"Agent class must implement '{method}' method",
                    )
                elif not callable(getattr(agent_class, method)):
                    result.add_error(
                        "agent_class",
                        f"'{method}' must be callable",
                    )

        config_result = self.validate_config(default_config)
        result.merge(config_result)

        if required_tools:
            for tool in required_tools:
                if not isinstance(tool, str):
                    result.add_error(
                        "required_tools",
                        f"Tool name must be string, got {type(tool).__name__}",
                        tool,
                    )

        return result

    def validate_config(
        self,
        config: dict[str, Any],
        blueprint_name: str | None = None,
    ) -> ValidationResult:
        """Validate agent configuration."""
        result = ValidationResult(valid=True)

        if "max_iterations" in config:
            max_iter = config["max_iterations"]
            if not isinstance(max_iter, int):
                result.add_error("max_iterations", "Must be an integer", max_iter)
            elif max_iter < 1:
                result.add_error("max_iterations", "Must be at least 1", max_iter)
            elif max_iter > 100:
                result.add_warning("max_iterations", "Very high value may cause issues", max_iter)

        if "timeout_seconds" in config:
            timeout = config["timeout_seconds"]
            if not isinstance(timeout, (int, float)):
                result.add_error("timeout_seconds", "Must be a number", timeout)
            elif timeout < 1:
                result.add_error("timeout_seconds", "Must be at least 1 second", timeout)
            elif timeout > 3600:
                result.add_warning("timeout_seconds", "Very long timeout", timeout)

        if "confidence_threshold" in config:
            threshold = config["confidence_threshold"]
            if not isinstance(threshold, (int, float)):
                result.add_error("confidence_threshold", "Must be a number", threshold)
            elif not 0 <= threshold <= 1:
                result.add_error("confidence_threshold", "Must be between 0 and 1", threshold)

        if "require_human_approval" in config and not isinstance(
            config["require_human_approval"], bool
        ):
            result.add_error(
                "require_human_approval",
                "Must be a boolean",
                config["require_human_approval"],
            )

        if "allowed_tools" in config:
            tools = config["allowed_tools"]
            if not isinstance(tools, list):
                result.add_error("allowed_tools", "Must be a list", tools)
            else:
                for i, tool in enumerate(tools):
                    if not isinstance(tool, str):
                        result.add_error(
                            f"allowed_tools[{i}]",
                            "Tool name must be string",
                            tool,
                        )

        if blueprint_name and blueprint_name in self._custom_validators:
            for validator in self._custom_validators[blueprint_name]:
                try:
                    custom_result = validator(config)
                    result.merge(custom_result)
                except Exception as e:
                    result.add_error("custom_validation", str(e))

        return result

    def validate_agent_creation(
        self,
        blueprint_name: str,
        tenant_id: str,
        agent_name: str,
        config_overrides: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate agent creation request."""
        result = ValidationResult(valid=True)

        if not blueprint_name:
            result.add_error("blueprint_name", "Blueprint name is required")

        if not tenant_id:
            result.add_error("tenant_id", "Tenant ID is required")

        if not agent_name:
            result.add_error("agent_name", "Agent name is required")
        elif len(agent_name) > 100:
            result.add_error("agent_name", "Agent name too long (max 100 chars)")

        if config_overrides:
            config_result = self.validate_config(config_overrides, blueprint_name)
            result.merge(config_result)

        return result

    def validate_execution_input(
        self,
        input_data: dict[str, Any],
        required_fields: list[str] | None = None,
    ) -> ValidationResult:
        """Validate execution input data."""
        result = ValidationResult(valid=True)

        if not isinstance(input_data, dict):
            result.add_error("input_data", "Must be a dictionary")
            return result

        if required_fields:
            for field_name in required_fields:
                if field_name not in input_data:
                    result.add_error(field_name, f"Required field '{field_name}' is missing")
                elif input_data[field_name] is None:
                    result.add_error(field_name, f"Required field '{field_name}' cannot be null")

        return result


_default_validator: BlueprintValidator | None = None


def get_blueprint_validator() -> BlueprintValidator:
    """Get the default blueprint validator."""
    global _default_validator
    if _default_validator is None:
        _default_validator = BlueprintValidator()
    return _default_validator
