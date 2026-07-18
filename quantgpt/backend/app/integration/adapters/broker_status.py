"""OpenAlgo Broker Status adapter."""

from __future__ import annotations

from app.integration.adapters.base import BaseOpenAlgoAdapter
from app.integration.models import BrokerStatus


class OpenAlgoBrokerStatusAdapter(BaseOpenAlgoAdapter):
    def get_status(self) -> BrokerStatus:
        reachable = self.ping()
        return BrokerStatus(
            base_url=self._http.base_url,
            reachable=reachable,
            api_key_configured=bool(self._api_key),
            websocket_url="",  # filled by facade which has ws url
            detail="reachable" if reachable else "unreachable",
        )

    def ping(self) -> bool:
        try:
            data = self._post("/api/v1/ping")
            return bool(data) or data == "success"
        except Exception:
            return False
