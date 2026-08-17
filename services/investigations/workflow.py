"""Bounded V1 investigation orchestration.

This is intentionally an explicit, testable workflow.  It can later be lifted
into LangGraph nodes without allowing model output to execute arbitrary tools.
"""

import re
from datetime import timedelta

from .collectors import BaseCollector, SeededCollector
from .repository import InvestigationRepository
from .schemas import Claim, CollectionPlan, Entity, Investigation, InvestigationStatus, Report, SourceType, utc_now


class InvestigationWorkflow:
    def __init__(self, repository: InvestigationRepository, collectors: dict[SourceType, BaseCollector] | None = None) -> None:
        self.repository = repository
        self.collectors = collectors or {kind: SeededCollector(kind) for kind in SourceType}

    def plan(self, investigation: Investigation) -> CollectionPlan:
        self.repository.log(investigation.id, "Planner", "Planning investigation")
        plan = CollectionPlan(
            target_entities=[investigation.target],
            topics=["activities", "announcements", "partnerships", "events"],
            time_range={"start": (utc_now() - timedelta(days=30)).date().isoformat(), "end": utc_now().date().isoformat()},
            required_sources=sorted(investigation.source_types, key=lambda source: source.value),
            research_questions=["What happened?", "When?", "Where?", "Who is involved?", "What evidence supports the event?"],
        )
        self.repository.plans[investigation.id] = plan
        self.repository.log(investigation.id, "Planner", f"{len(plan.research_questions)} research questions generated")
        return plan

    def collect(self, investigation: Investigation, plan: CollectionPlan) -> int:
        self.repository.log(investigation.id, "Collection Controller", f"Creating {len(plan.required_sources)} collection jobs")
        collected = 0
        for source_type in plan.required_sources:
            collector = self.collectors.get(source_type)
            if collector is None:
                self.repository.log(investigation.id, "Collection Controller", f"No collector configured for {source_type.value}")
                continue
            try:
                for item in collector.collect(investigation.target):
                    if self.repository.add_item(investigation.id, collector.normalize(item), collector.name):
                        collected += 1
            except Exception as exc:  # a failed source must not fail an investigation
                self.repository.log(investigation.id, collector.name, f"Collection failed: {exc}")
        self.repository.log(investigation.id, "Collection Controller", f"{collected} unique documents preserved")
        return collected

    def analyse(self, investigation: Investigation) -> None:
        evidence_rows = self.repository.evidence[investigation.id]
        self.repository.log(investigation.id, "Analyst", "Extracting entities and claims")
        entities: dict[str, Entity] = {}
        claims: list[Claim] = []
        for evidence in evidence_rows:
            names = re.findall(r"\b[A-Z][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*\b", evidence.content)
            for name in names:
                if len(name) < 3:
                    continue
                key = name.lower()
                if key not in entities:
                    entities[key] = Entity(entity_id=f"ENT-{len(entities)+1:04d}", name=name, entity_type="UNKNOWN", evidence_ids=[])
                entities[key].evidence_ids.append(evidence.evidence_id)
            for sentence in re.split(r"(?<=[.!?])\s+", evidence.content.strip()):
                if len(sentence) >= 25:
                    claim = Claim(claim_id=f"CLM-{len(claims)+1:04d}", text=sentence, evidence_ids=[evidence.evidence_id])
                    claims.append(claim)
                    evidence.relationships["supports_claims"].append(claim.claim_id)
        self.repository.entities[investigation.id] = list(entities.values())
        self.repository.claims[investigation.id] = claims
        self.repository.log(investigation.id, "Analyst", f"{len(entities)} entities and {len(claims)} claims extracted")

    def verify(self, investigation: Investigation) -> None:
        for claim in self.repository.claims[investigation.id]:
            # V1 rule: direct preserved source text supports an extracted claim.
            claim.status = "supported" if claim.evidence_ids else "insufficient"
            claim.model_assessed_confidence = 0.6 if claim.evidence_ids else 0.0
        self.repository.log(investigation.id, "Verifier", f"Checked {len(self.repository.claims[investigation.id])} claims")

    def report(self, investigation: Investigation) -> Report:
        claims = self.repository.claims[investigation.id]
        report = Report(
            investigation_id=investigation.id,
            executive_summary=f"Investigation of {investigation.target} preserved {len(self.repository.evidence[investigation.id])} evidence records.",
            key_findings=[f"{claim.text} (Evidence: {', '.join(claim.evidence_ids)})" for claim in claims[:10]],
        )
        self.repository.reports[investigation.id] = report
        self.repository.log(investigation.id, "Reporter", "Evidence-linked report generated")
        return report

    def run(self, investigation: Investigation) -> Report:
        investigation.status = InvestigationStatus.RUNNING
        plan = self.plan(investigation)
        self.collect(investigation, plan)
        self.analyse(investigation)
        self.verify(investigation)
        report = self.report(investigation)
        investigation.status = InvestigationStatus.COMPLETE
        return report
