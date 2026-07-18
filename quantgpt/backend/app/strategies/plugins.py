"""Plugin loader for external strategies.

Loads strategy plugins from Python modules. A plugin module must define
a `create_strategy()` function that returns a StrategyBase instance,
or a `STRATEGY_CLASS` attribute pointing to a StrategyBase subclass.

Plugin discovery:
  1. Explicit module paths passed to load_plugin()
  2. Auto-discovery from a plugins/ directory (optional)

No live trading — plugins are research/intelligence only.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from typing import Any

from app.logging.config import get_logger
from app.strategies.base import StrategyBase
from app.strategies.registry import StrategyRegistry

_log = get_logger("strategy.plugins")


def load_plugin_from_module(module_path: str, registry: StrategyRegistry) -> StrategyBase | None:
    """Load a strategy plugin from a module path.

    The module must expose either:
      - `create_strategy() -> StrategyBase`  (preferred)
      - `STRATEGY_CLASS: type[StrategyBase]`  (alternative)

    Returns the registered strategy, or None if loading failed.
    """
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        _log.warning("plugin.import_failed", module=module_path, error=str(e))
        return None

    strategy: StrategyBase | None = None

    if hasattr(mod, "create_strategy"):
        strategy = mod.create_strategy()
    elif hasattr(mod, "STRATEGY_CLASS"):
        strategy = mod.STRATEGY_CLASS()

    if strategy is None or not isinstance(strategy, StrategyBase):
        _log.warning("plugin.invalid", module=module_path, reason="no create_strategy() or STRATEGY_CLASS")
        return None

    if registry.contains(strategy.name):
        _log.warning("plugin.duplicate", module=module_path, name=strategy.name)
        return None

    # Mark as plugin
    strategy_dict = strategy.to_dict()
    strategy_dict["is_plugin"] = True
    strategy_dict["source"] = module_path

    registry.register(strategy)
    _log.info("plugin.loaded", module=module_path, name=strategy.name, version=strategy.version)
    return strategy


def load_plugin_from_file(file_path: str, registry: StrategyRegistry) -> StrategyBase | None:
    """Load a strategy plugin from a .py file path."""
    if not os.path.exists(file_path):
        _log.warning("plugin.file_not_found", path=file_path)
        return None

    module_name = f"strategy_plugin_{os.path.basename(file_path).replace('.py', '')}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        _log.warning("plugin.spec_failed", path=file_path)
        return None

    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        _log.warning("plugin.exec_failed", path=file_path, error=str(e))
        return None

    strategy: StrategyBase | None = None
    if hasattr(mod, "create_strategy"):
        strategy = mod.create_strategy()
    elif hasattr(mod, "STRATEGY_CLASS"):
        strategy = mod.STRATEGY_CLASS()

    if strategy is None or not isinstance(strategy, StrategyBase):
        _log.warning("plugin.invalid", path=file_path, reason="no create_strategy() or STRATEGY_CLASS")
        return None

    if registry.contains(strategy.name):
        _log.warning("plugin.duplicate", path=file_path, name=strategy.name)
        return None

    registry.register(strategy)
    _log.info("plugin.loaded_from_file", path=file_path, name=strategy.name, version=strategy.version)
    return strategy


def discover_plugins(plugins_dir: str, registry: StrategyRegistry) -> list[str]:
    """Auto-discover plugin .py files in a directory. Returns list of
    loaded strategy names."""
    loaded: list[str] = []
    if not os.path.isdir(plugins_dir):
        return loaded

    for filename in sorted(os.listdir(plugins_dir)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        path = os.path.join(plugins_dir, filename)
        strategy = load_plugin_from_file(path, registry)
        if strategy:
            loaded.append(strategy.name)

    return loaded
