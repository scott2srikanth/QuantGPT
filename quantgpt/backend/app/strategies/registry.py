"""Strategy Registry — in-memory registry of all available strategies.

Built-in strategies are registered at construction. Plugin strategies
are registered dynamically via the plugin loader.
"""

from __future__ import annotations

from typing import Any

from app.strategies.base import StrategyBase
from app.strategies.builtins import BUILTIN_STRATEGIES


class StrategyAlreadyRegisteredError(Exception):
    """A strategy with this name is already registered."""


class StrategyNotFoundError(Exception):
    """Requested strategy is not registered."""


class StrategyRegistry:
    """In-memory registry of strategy name → StrategyBase instance."""

    def __init__(self) -> None:
        self._strategies: dict[str, StrategyBase] = {}

    def register(self, strategy: StrategyBase) -> StrategyBase:
        if strategy.name in self._strategies:
            raise StrategyAlreadyRegisteredError(f"Strategy '{strategy.name}' already registered")
        self._strategies[strategy.name] = strategy
        return strategy

    def get(self, name: str) -> StrategyBase:
        if name not in self._strategies:
            raise StrategyNotFoundError(f"Strategy '{name}' not found")
        return self._strategies[name]

    def all(self) -> dict[str, StrategyBase]:
        return dict(self._strategies)

    def names(self) -> list[str]:
        return list(self._strategies.keys())

    def contains(self, name: str) -> bool:
        return name in self._strategies

    def __len__(self) -> int:
        return len(self._strategies)

    def list_all(self) -> list[dict[str, Any]]:
        """Return serializable info for all registered strategies."""
        return [s.to_dict() for s in self._strategies.values()]


def build_registry() -> StrategyRegistry:
    """Build a registry with all built-in strategies pre-registered."""
    registry = StrategyRegistry()
    for cls in BUILTIN_STRATEGIES:
        registry.register(cls())
    return registry
