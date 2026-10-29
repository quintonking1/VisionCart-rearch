"""Shared state passed between agents, plus the dependencies every node gets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, Field

from visioncart.catalog.search import CatalogSearch
from visioncart.catalog.store import Catalog
from visioncart.llm import LLMClient
from visioncart.memory.store import StyleMemory

UNAVAILABLE = "unavailable"


class PlannedItem(BaseModel):
    requested_as: str = Field(description="The user's own words for this item, e.g. 'rain boots'.")
    category: str = Field(description="Exactly one of the catalog categories, or 'unavailable'.")
    description: str = Field(description="What a good match looks like, in the user's style.")
    cluster_id: int = Field(description="Id of the style cluster this item should follow.")
    max_price: float | None = Field(description="Per-item price cap in USD if the user gave one.")
    size: str | None = Field(description="Clothing or shoe size if the user gave one.")
    needs_water_resistant: bool = Field(description="True if weather or use calls for it.")


class Plan(BaseModel):
    items: list[PlannedItem]
    total_budget: float | None = Field(description="Total budget in USD across all items, if given.")
    occasion: str | None


@dataclass
class Scored:
    product_id: str
    visual: float
    bias: float
    failures: list[str] = field(default_factory=list)
    retrieval: float = 0.0
    rank: float = 0.0  # blended ordering score; see verifier.score_candidates

    @property
    def score(self) -> float:
        """Style-fit score that the calibrated threshold gates on."""
        return self.visual + self.bias


@dataclass
class ItemResult:
    index: int
    item: PlannedItem
    accepted: list[Scored]
    explanations: dict[str, str]
    attempts: int
    low_confidence: bool
    note: str | None = None


@dataclass
class Deps:
    llm: LLMClient
    catalog: Catalog
    search: CatalogSearch
    memory: StyleMemory
    threshold: float
    blend: float = 0.0  # weight on worker retrieval score when ordering verified products
    worker: Callable[..., Any] | None = None  # None = catalog search worker; live mode swaps in the web worker
    max_retries: int | None = None            # None = config.MAX_RETRIES
    progress: Callable[[str, PlannedItem, dict], None] | None = None  # UI progress events (live mode)
