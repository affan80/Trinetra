"""Collector contracts and a safe seeded collector for the V1 demo path."""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from .schemas import NormalizedItem, SourceType


class BaseCollector(ABC):
    name: str = "base"
    source_type: SourceType

    @abstractmethod
    def search(self, query: str) -> Iterable[NormalizedItem]:
        raise NotImplementedError

    def collect(self, target: str) -> Iterable[NormalizedItem]:
        return self.search(target)

    def normalize(self, item: NormalizedItem) -> NormalizedItem:
        return item


class SeededCollector(BaseCollector):
    """A deterministic collector used when no permitted external source is set up.

    It makes the complete evidence workflow demonstrable without claiming that
    synthetic records are live OSINT.  Production adapters implement the same
    contract and are registered by the application configuration.
    """

    name = "seeded_v1"

    def __init__(self, source_type: SourceType) -> None:
        self.source_type = source_type

    def search(self, query: str) -> Iterable[NormalizedItem]:
        label = self.source_type.value.title()
        yield NormalizedItem(
            source_type=self.source_type,
            title=f"{label} record concerning {query}",
            url=f"https://demo.invalid/{self.source_type.value}/{query.lower().replace(' ', '-')}",
            publisher="Trinetra V1 demonstration source",
            text=(
                f"Demonstration {label.lower()} record about {query}. "
                "This seeded item validates the provenance and verification workflow."
            ),
            metadata={"demo_data": True},
        )
