"""Placeholder agents for the QuantGPT multi-agent framework.

Each agent is a thin subclass of AgentBase with a name, type, and a
placeholder execute() that returns a stub result. These establish the
architecture and the uniform interface; implementation comes later.

All 15 agents:
  Market Scanner, Technical Analysis, Fundamental Analysis, News,
  Risk, Portfolio, Strategy, Trade Decision, Backtesting, Prediction,
  Self Evaluation, Reporting, Trade Journal, Monitoring, Alerting.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentBase


class _PlaceholderAgent(AgentBase):
    """Common placeholder implementation. Subclasses set name + type."""

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent": self.name,
            "type": self.type,
            "status": "placeholder",
            "message": f"{self.name} is a placeholder — not yet implemented",
            "payload": payload,
        }


class MarketScannerAgent(_PlaceholderAgent):
    name = "market_scanner"
    type = "scanner"


class TechnicalAnalysisAgent(_PlaceholderAgent):
    name = "technical_analysis"
    type = "analysis"


class FundamentalAnalysisAgent(_PlaceholderAgent):
    name = "fundamental_analysis"
    type = "analysis"


class NewsAgent(_PlaceholderAgent):
    name = "news"
    type = "information"


class RiskAgent(_PlaceholderAgent):
    name = "risk"
    type = "risk"


class PortfolioAgent(_PlaceholderAgent):
    name = "portfolio"
    type = "portfolio"


class StrategyAgent(_PlaceholderAgent):
    name = "strategy"
    type = "strategy"


class TradeDecisionAgent(_PlaceholderAgent):
    name = "trade_decision"
    type = "decision"


class BacktestingAgent(_PlaceholderAgent):
    name = "backtesting"
    type = "backtesting"


class PredictionAgent(_PlaceholderAgent):
    name = "prediction"
    type = "prediction"


class SelfEvaluationAgent(_PlaceholderAgent):
    name = "self_evaluation"
    type = "evaluation"


class ReportingAgent(_PlaceholderAgent):
    name = "reporting"
    type = "reporting"


class TradeJournalAgent(_PlaceholderAgent):
    name = "trade_journal"
    type = "journal"


class MonitoringAgent(_PlaceholderAgent):
    name = "monitoring"
    type = "monitoring"


class AlertingAgent(_PlaceholderAgent):
    name = "alerting"
    type = "alerting"


# Ordered list for deterministic registration.
ALL_AGENT_CLASSES: list[type[_PlaceholderAgent]] = [
    MarketScannerAgent,
    TechnicalAnalysisAgent,
    FundamentalAnalysisAgent,
    NewsAgent,
    RiskAgent,
    PortfolioAgent,
    StrategyAgent,
    TradeDecisionAgent,
    BacktestingAgent,
    PredictionAgent,
    SelfEvaluationAgent,
    ReportingAgent,
    TradeJournalAgent,
    MonitoringAgent,
    AlertingAgent,
]
