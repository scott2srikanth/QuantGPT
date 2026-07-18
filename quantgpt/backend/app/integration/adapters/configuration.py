"""OpenAlgo Configuration adapter.

Reads and writes OpenAlgo-side settings via /api/v1 endpoints. Used by
QuantGPT to inspect or adjust backend configuration without modifying
OpenAlgo source.
"""

from __future__ import annotations

from app.integration.adapters.base import BaseOpenAlgoAdapter


class OpenAlgoConfigurationAdapter(BaseOpenAlgoAdapter):
    def get_config(self, key: str) -> str | None:
        try:
            data = self._post("/api/v1/settings", {"action": "get", "key": key})
            if isinstance(data, dict):
                return data.get("value")
            return data
        except Exception:
            return None

    def set_config(self, key: str, value: str) -> None:
        self._post("/api/v1/settings", {"action": "set", "key": key, "value": value})

    def list_config(self) -> dict[str, str]:
        data = self._post("/api/v1/settings", {"action": "list"})
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items()}
        return {}
