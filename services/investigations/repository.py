"""Small repository preserving raw artifacts and normalized evidence locally.

The interface is deliberately storage-agnostic so a Postgres/MinIO adapter can
replace it without changing agents or API contracts.
"""

from collections import defaultdict
from hashlib import sha256
from pathlib import Path

from .schemas import AgentActivity, Claim, Entity, Evidence, Investigation, MediaArtifact, NormalizedItem, Provenance, Report


class InvestigationRepository:
    def __init__(self, raw_root: Path | str = "data/raw/investigations") -> None:
        self.raw_root = Path(raw_root)
        self.investigations: dict[str, Investigation] = {}
        self.plans: dict[str, object] = {}
        self.evidence: dict[str, list[Evidence]] = defaultdict(list)
        self.entities: dict[str, list[Entity]] = defaultdict(list)
        self.claims: dict[str, list[Claim]] = defaultdict(list)
        self.activities: dict[str, list[AgentActivity]] = defaultdict(list)
        self.reports: dict[str, Report] = {}
        self.artifacts: dict[str, list[MediaArtifact]] = defaultdict(list)

    def next_id(self, prefix: str, items: list[object] | dict[str, object]) -> str:
        return f"{prefix}-{len(items) + 1:04d}"

    def save_raw(self, investigation_id: str, content: bytes, suffix: str = ".txt") -> tuple[str, str]:
        digest = sha256(content).hexdigest()
        path = self.raw_root / investigation_id / f"{digest}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(content)
        return digest, str(path)

    def add_item(self, investigation_id: str, item: NormalizedItem, collector: str) -> Evidence | None:
        raw = item.raw or item.text.encode("utf-8")
        digest, raw_path = self.save_raw(investigation_id, raw)
        if any(row.provenance.content_hash == digest for row in self.evidence[investigation_id]):
            return None
        number = len(self.evidence[investigation_id]) + 1
        evidence = Evidence(
            evidence_id=f"EVD-{number:04d}",
            source_id=f"SRC-{number:04d}",
            document_id=f"DOC-{number:04d}",
            content=item.text,
            location={"page": None, "paragraph": 1, "timestamp": None},
            provenance=Provenance(
                url=item.url,
                source_type=item.source_type,
                published_at=item.published_at,
                collector=collector,
                content_hash=digest,
                raw_path=raw_path,
            ),
        )
        self.evidence[investigation_id].append(evidence)
        return evidence

    def log(self, investigation_id: str, agent: str, message: str) -> None:
        self.activities[investigation_id].append(AgentActivity(agent=agent, message=message))
