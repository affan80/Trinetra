from pathlib import Path

from services.investigations.collectors import BaseCollector
from services.investigations.repository import InvestigationRepository
from services.investigations.schemas import (
    Investigation,
    InvestigationStatus,
    NormalizedItem,
    SourceType,
)
from services.investigations.workflow import InvestigationWorkflow


class FailingCollector(BaseCollector):
    name = "failing"
    source_type = SourceType.NEWS

    def search(self, query):
        raise RuntimeError("permitted source unavailable")


class StaticCollector(BaseCollector):
    name = "static"
    source_type = SourceType.WEB

    def search(self, query):
        yield NormalizedItem(
            source_type=SourceType.WEB,
            title="Announcement",
            url="https://example.test/announcement",
            text="Organization X announced Event Y in Delhi on 12 August.",
        )


def make_investigation():
    return Investigation(
        id="INV-0001",
        title="Investigate Organization X",
        target="Organization X",
        objective="Investigate recent activities",
        source_types={SourceType.WEB, SourceType.NEWS},
    )


def test_workflow_preserves_raw_evidence_and_links_claims(tmp_path: Path):
    repository = InvestigationRepository(tmp_path)
    investigation = make_investigation()
    repository.investigations[investigation.id] = investigation
    workflow = InvestigationWorkflow(
        repository,
        {SourceType.WEB: StaticCollector(), SourceType.NEWS: FailingCollector()},
    )

    report = workflow.run(investigation)

    evidence = repository.evidence[investigation.id]
    claims = repository.claims[investigation.id]
    assert investigation.status == InvestigationStatus.COMPLETE
    assert len(evidence) == 1
    assert Path(evidence[0].provenance.raw_path).read_text() == evidence[0].content
    assert evidence[0].provenance.content_hash
    assert claims[0].evidence_ids == [evidence[0].evidence_id]
    assert claims[0].status == "supported"
    assert "EVD-0001" in report.key_findings[0]
    assert any("Collection failed" in item.message for item in repository.activities[investigation.id])


def test_repository_deduplicates_by_raw_content_hash(tmp_path: Path):
    repository = InvestigationRepository(tmp_path)
    item = next(StaticCollector().collect("Organization X"))

    first = repository.add_item("INV-0001", item, "static")
    second = repository.add_item("INV-0001", item, "static")

    assert first is not None
    assert second is None
