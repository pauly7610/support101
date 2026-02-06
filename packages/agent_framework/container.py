"""
Dependency Injection Container for Agent Framework.

Replaces singleton pattern with proper DI for better testability and flexibility.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from .persistence.base import StateStore
from .persistence.memory import InMemoryStateStore

T = TypeVar("T")


@dataclass
class ServiceConfig:
    """Configuration for a service registration."""

    factory: Callable[..., Any]
    singleton: bool = True
    instance: Any | None = None


class Container:
    """
    Dependency injection container.

    Manages service registration, resolution, and lifecycle.
    Supports both singleton and transient services.

    Usage:
        container = Container()
        container.register(StateStore, lambda: RedisStateStore(url))

        store = container.resolve(StateStore)
    """

    def __init__(self) -> None:
        self._services: dict[type, ServiceConfig] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default implementations."""
        self.register(StateStore, InMemoryStateStore, singleton=True)

    def register(
        self,
        service_type: type[T],
        factory: Callable[..., T],
        singleton: bool = True,
    ) -> None:
        """
        Register a service.

        Args:
            service_type: The type/interface to register
            factory: Factory function or class to create instances
            singleton: If True, only one instance is created
        """
        self._services[service_type] = ServiceConfig(
            factory=factory,
            singleton=singleton,
            instance=None,
        )

    def register_instance(self, service_type: type[T], instance: T) -> None:
        """Register an existing instance as a singleton."""
        self._services[service_type] = ServiceConfig(
            factory=lambda: instance,
            singleton=True,
            instance=instance,
        )

    def resolve(self, service_type: type[T]) -> T:
        """
        Resolve a service.

        Args:
            service_type: The type to resolve

        Returns:
            Service instance

        Raises:
            KeyError: If service is not registered
        """
        if service_type not in self._services:
            raise KeyError(f"Service {service_type.__name__} not registered")

        config = self._services[service_type]

        if config.singleton and config.instance is not None:
            return config.instance

        instance = config.factory()

        if config.singleton:
            config.instance = instance

        return instance

    def try_resolve(self, service_type: type[T]) -> T | None:
        """Resolve a service, returning None if not registered."""
        try:
            return self.resolve(service_type)
        except KeyError:
            return None

    def is_registered(self, service_type: type) -> bool:
        """Check if a service is registered."""
        return service_type in self._services

    def reset(self, service_type: type | None = None) -> None:
        """
        Reset service instances.

        Args:
            service_type: Specific service to reset, or None for all
        """
        if service_type:
            if service_type in self._services:
                self._services[service_type].instance = None
        else:
            for config in self._services.values():
                config.instance = None

    def clear(self) -> None:
        """Clear all registrations."""
        self._services.clear()
        self._register_defaults()


_default_container: Container | None = None


def get_container() -> Container:
    """Get the default container instance."""
    global _default_container
    if _default_container is None:
        _default_container = Container()
    return _default_container


def set_container(container: Container) -> None:
    """Set the default container instance."""
    global _default_container
    _default_container = container


def reset_container() -> None:
    """Reset the default container."""
    if _default_container:
        _default_container.reset()


class Injectable:
    """
    Mixin for classes that support dependency injection.

    Usage:
        class MyService(Injectable):
            def __init__(self, container: Optional[Container] = None):
                super().__init__(container)
                self.store = self.inject(StateStore)
    """

    def __init__(self, container: Container | None = None) -> None:
        self._container = container or get_container()

    def inject(self, service_type: type[T]) -> T:
        """Inject a dependency."""
        return self._container.resolve(service_type)

    def try_inject(self, service_type: type[T]) -> T | None:
        """Try to inject a dependency, returning None if not available."""
        return self._container.try_resolve(service_type)
