"""Strategy Marketplace — discover, publish, and rate strategies.

The marketplace is backed by Supabase tables (marketplace_listings,
strategies). It provides:
  - List published strategies with filtering by tags/type
  - Publish a strategy to the marketplace
  - Rate a strategy (0-5 stars)
  - Download/install a strategy (increments download count)
  - Feature/unfeature strategies

No live trading — marketplace is for research/intelligence only.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.logging.config import get_logger
from app.strategies.base import StrategyBase
from app.strategies.registry import StrategyRegistry

_log = get_logger("strategy.marketplace")


class MarketplaceListing:
    """In-memory representation of a marketplace listing."""

    def __init__(
        self,
        *,
        strategy_name: str,
        title: str,
        description: str = "",
        author: str = "",
        tags: list[str] | None = None,
        rating: float = 0.0,
        downloads: int = 0,
        is_featured: bool = False,
        is_published: bool = False,
        listing_id: str | None = None,
    ) -> None:
        self.id = listing_id or str(uuid.uuid4())
        self.strategy_name = strategy_name
        self.title = title
        self.description = description
        self.author = author
        self.tags = tags or []
        self.rating = rating
        self.downloads = downloads
        self.is_featured = is_featured
        self.is_published = is_published

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "strategy_name": self.strategy_name,
            "title": self.title,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "rating": self.rating,
            "downloads": self.downloads,
            "is_featured": self.is_featured,
            "is_published": self.is_published,
        }


class StrategyMarketplace:
    """Manages strategy marketplace listings.

    Listings are kept in-memory for fast access and can be synced to/from
    Supabase. The marketplace does NOT execute trades — it's a discovery
    and evaluation layer for research strategies.
    """

    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry
        self._listings: dict[str, MarketplaceListing] = {}  # strategy_name → listing

    def publish(
        self,
        strategy_name: str,
        *,
        title: str | None = None,
        description: str = "",
        author: str = "",
        tags: list[str] | None = None,
    ) -> MarketplaceListing:
        """Publish a registered strategy to the marketplace."""
        strategy = self._registry.get(strategy_name)
        listing = MarketplaceListing(
            strategy_name=strategy_name,
            title=title or strategy.display_name,
            description=description or strategy.description,
            author=author,
            tags=tags or [strategy.type],
            is_published=True,
        )
        self._listings[strategy_name] = listing
        _log.info("marketplace.published", strategy=strategy_name, title=listing.title)
        return listing

    def unpublish(self, strategy_name: str) -> None:
        if strategy_name in self._listings:
            self._listings[strategy_name].is_published = False

    def list_published(self, *, tag: str | None = None, strategy_type: str | None = None) -> list[dict[str, Any]]:
        """List all published strategies, optionally filtered by tag or type."""
        results = []
        for listing in self._listings.values():
            if not listing.is_published:
                continue
            if tag and tag not in listing.tags:
                continue
            if strategy_type:
                strategy = self._registry.get(listing.strategy_name)
                if strategy.type != strategy_type:
                    continue
            entry = listing.to_dict()
            entry["strategy_info"] = self._registry.get(listing.strategy_name).to_dict()
            results.append(entry)
        # Sort: featured first, then by rating, then by downloads
        results.sort(key=lambda r: (not r["is_featured"], -r["rating"], -r["downloads"]))
        return results

    def rate(self, strategy_name: str, rating: float) -> MarketplaceListing:
        """Rate a strategy (0-5 stars). Updates the listing's rating."""
        if strategy_name not in self._listings:
            raise KeyError(f"Strategy '{strategy_name}' not in marketplace")
        if not 0 <= rating <= 5:
            raise ValueError("Rating must be between 0 and 5")
        listing = self._listings[strategy_name]
        # Simple rating update (in a real system, this would average all user ratings)
        listing.rating = rating
        return listing

    def download(self, strategy_name: str) -> dict[str, Any]:
        """Download a strategy (increments download count, returns strategy info)."""
        if strategy_name not in self._listings:
            raise KeyError(f"Strategy '{strategy_name}' not in marketplace")
        self._listings[strategy_name].downloads += 1
        strategy = self._registry.get(strategy_name)
        return {
            "strategy": strategy.to_dict(),
            "config_schema": strategy.config_schema(),
            "default_config": strategy.default_config(),
            "downloads": self._listings[strategy_name].downloads,
        }

    def feature(self, strategy_name: str) -> MarketplaceListing:
        if strategy_name not in self._listings:
            raise KeyError(f"Strategy '{strategy_name}' not in marketplace")
        self._listings[strategy_name].is_featured = True
        return self._listings[strategy_name]

    def unfeature(self, strategy_name: str) -> MarketplaceListing:
        if strategy_name not in self._listings:
            raise KeyError(f"Strategy '{strategy_name}' not in marketplace")
        self._listings[strategy_name].is_featured = False
        return self._listings[strategy_name]

    def get_listing(self, strategy_name: str) -> dict[str, Any] | None:
        if strategy_name not in self._listings:
            return None
        listing = self._listings[strategy_name]
        entry = listing.to_dict()
        entry["strategy_info"] = self._registry.get(strategy_name).to_dict()
        return entry

    def all_listings(self) -> list[dict[str, Any]]:
        return [l.to_dict() for l in self._listings.values()]


def build_marketplace(registry: StrategyRegistry) -> StrategyMarketplace:
    """Build a marketplace with all built-in strategies auto-published."""
    mp = StrategyMarketplace(registry)
    for name, strategy_cls in registry.all().items():
        mp.publish(
            name,
            title=strategy_cls.display_name,
            description=strategy_cls.description,
            author="QuantGPT",
            tags=[strategy_cls.type, "builtin"],
        )
    return mp
