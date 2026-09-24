"""The overview must reflect stored data and respect watchlist ownership."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.core.security import decode_access_token
from backend.app.db.database import Base, get_db
from backend.app.db.models import (
    CanonicalRecord, CollectionJob, CollectionPlan, DuplicateCluster,
    DuplicateClusterMember, Location, MonitoringProfile, RawObject,
    RecordQuality, Source, Watchlist, WatchlistLocation,
)
from backend.app.main import app
from backend.app.services.evidence_service import preserve
from backend.app.services.object_store import ObjectStore
from scripts import audit_source_registry


def test_overview_is_live_and_private(tmp_path, monkeypatch):
    monkeypatch.setenv("TRINETRA_AUTO_SEED", "false")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def test_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    client = TestClient(app)
    try:
        owner_token = client.post("/api/v1/auth/register", json={"email": "overview-owner@example.com", "password": "test-password-123"}).json()["access_token"]
        other_token = client.post("/api/v1/auth/register", json={"email": "overview-other@example.com", "password": "test-password-123"}).json()["access_token"]
        owner_id = UUID(decode_access_token(owner_token)["sub"])

        with Session(engine) as db:
            source = Source(name="Example feed", source_class="NEWS", adapter_name="rss")
            watchlist = Watchlist(name="Test region", objective="Observe published reports", created_by=owner_id)
            db.add_all([source, watchlist])
            db.flush()
            location = Location(name="Test site", latitude=34.5, longitude=77.1, location_type="REGION")
            db.add(location)
            db.flush()
            db.add(WatchlistLocation(watchlist_id=watchlist.id, location_id=location.id))
            profile = MonitoringProfile(watchlist_id=watchlist.id, version=1, status="ACTIVE", payload={})
            db.add(profile)
            db.flush()
            plan = CollectionPlan(profile_id=profile.id, source_id=source.id, created_by=owner_id)
            db.add(plan)
            db.flush()
            job = CollectionJob(plan_id=plan.id, profile_id=profile.id, source_id=source.id,
                                fingerprint="a" * 64, query="test region", language="en", status="QUEUED")
            db.add(job)
            db.flush()
            raw = RawObject(evidence_id="raw-1", job_id=job.id, source_id=source.id,
                            watchlist_id=watchlist.id, source_url="https://example.com/a",
                            final_url="https://example.com/a", adapter_type="rss",
                            object_uri="file:///tmp/raw-1", sha256="b" * 64, content_type="text/html",
                            content_length=123, http_status=200, collector_version="test")
            db.add(raw)
            db.add_all([
                CanonicalRecord(record_id="record-1", evidence_id="raw-1", source_id=source.id,
                                watchlist_id=watchlist.id, record_type="text", title="Observed activity",
                                canonical_url="https://example.com/a", plain_text="Extracted report body",
                                content_blocks=[{"type": "paragraph", "text": "Extracted report body"}]),
                CanonicalRecord(record_id="record-2", evidence_id="raw-2", source_id=source.id,
                                watchlist_id=watchlist.id, record_type="text", title="Repeated activity",
                                canonical_url="javascript:alert(1)"),
            ])
            db.flush()
            db.add(RecordQuality(record_id="record-1", status="VALID", quality_score=.91,
                                 quality_version="test"))
            cluster = DuplicateCluster(cluster_type="EXACT_TEXT", representative_record_id="record-1", member_count=2)
            db.add(cluster)
            db.flush()
            db.add_all([
                DuplicateClusterMember(cluster_id=cluster.id, record_id="record-1", relationship_type="REPRESENTATIVE", detection_method="test", decision_version="test"),
                DuplicateClusterMember(cluster_id=cluster.id, record_id="record-2", relationship_type="DUPLICATE", detection_method="test", decision_version="test"),
            ])
            db.commit()
            job_id, source_id, watchlist_id, location_id = job.id, source.id, watchlist.id, location.id

        assert client.get("/api/v1/overview").status_code == 401
        report = tmp_path / "source_audit_live.json"
        monkeypatch.setenv("SOURCE_AUDIT_REPORT", str(report))
        assert client.get("/api/v1/source-audit").status_code == 401
        assert client.get("/api/v1/source-audit", headers={"Authorization": f"Bearer {owner_token}"}).json()["status"] == "NOT_STARTED"
        report.write_text('{"status":"RUNNING","summary":{"total":2,"completed":1},"sources":[]}')
        assert client.get("/api/v1/source-audit", headers={"Authorization": f"Bearer {owner_token}"}).json()["summary"]["completed"] == 1
        report.write_text('''{"status":"COMPLETE","summary":{"total":2,"completed":2,"collected":1,"failed":1,"blocked":0,"forbidden":0,"skipped":0,"rss_feeds":1,"rss_entries":2},"sources":[{"id":"src-1","name":"Feed","base_url":"https://example.com","status":"COLLECTED","feeds":[{"rss_url":"https://example.com/rss","status":"COLLECTED","items":[{"title":"Delhi protest","url":"https://example.com/1"},{"title":"Unlocated report","url":"javascript:alert(1)"}]}]},{"id":"src-2","name":"Broken","base_url":"https://broken.example","status":"HTTP_522","http_status":522}]}''')
        outputs = client.get("/api/v1/source-audit/outputs?size=2&page=2", headers={"Authorization": f"Bearer {owner_token}"})
        assert outputs.status_code == 200
        assert outputs.json()["total"] == 4
        assert len(outputs.json()["items"]) == 2
        assert outputs.json()["items"][0]["type"] == "RSS_ENTRY"
        assert client.get("/api/v1/source-audit/outputs?status=HTTP_522", headers={"Authorization": f"Bearer {owner_token}"}).json()["total"] == 1
        assert client.get("/api/v1/source-audit/map").status_code == 401
        mapped = client.get("/api/v1/source-audit/map", headers={"Authorization": f"Bearer {owner_token}"}).json()
        assert mapped["total_entries"] == 2 and mapped["unmapped_entries"] == 1
        assert mapped["items"][0]["city"] == "Delhi"
        owner = client.get("/api/v1/overview", headers={"Authorization": f"Bearer {owner_token}"})
        assert owner.status_code == 200, owner.text
        data = owner.json()
        assert data["metrics"] == {"sources": 1, "raw_evidence": 1, "canonical_records": 2,
                                   "unique_evidence": 1, "duplicates": 1, "active_jobs": 1}
        assert data["watchlists"][0]["locations"][0]["latitude"] == 34.5
        assert data["watchlists"][0]["record_count"] == 2
        assert data["watchlists"][0]["source_count"] == 1
        assert next(record for record in data["records"] if record["id"] == "record-1")["quality_score"] == .91
        assert data["timeline"]
        lineage = client.get("/api/v1/overview/lineage/record-1", headers={"Authorization": f"Bearer {owner_token}"})
        assert lineage.status_code == 200, lineage.text
        assert lineage.json()["raw"]["id"] == "raw-1"
        assert lineage.json()["related"][0]["id"] == "record-2"
        incident = client.get(f"/api/v1/incidents/{watchlist_id}?location={location_id}", headers={"Authorization": f"Bearer {owner_token}"})
        assert incident.status_code == 200, incident.text
        assert incident.json()["locations"][0]["id"]
        assert incident.json()["selected_location_id"] == str(location_id)
        assert next(record for record in incident.json()["records"] if record["id"] == "record-1")["url"] == "https://example.com/a"
        assert next(record for record in incident.json()["records"] if record["id"] == "record-1")["plain_text"] == "Extracted report body"
        assert any(entry["kind"] == "raw" for entry in incident.json()["timeline"])
        assert next(record for record in incident.json()["records"] if record["id"] == "record-2")["url"] is None

        other = client.get("/api/v1/overview", headers={"Authorization": f"Bearer {other_token}"})
        assert other.status_code == 200
        assert other.json()["metrics"]["canonical_records"] == 0
        assert other.json()["watchlists"] == []
        assert client.get("/api/v1/overview/lineage/record-1", headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
        assert client.get(f"/api/v1/incidents/{watchlist_id}", headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
        assert client.get("/api/v1/incidents/00000000-0000-0000-0000-000000000000", headers={"Authorization": f"Bearer {owner_token}"}).status_code == 404

        with Session(engine) as db:
            saved = preserve(db, db.get(CollectionJob, job_id), db.get(Source, source_id), {
                "body": b"Collected public report",
                "requested_url": "https://example.com/report",
                "final_url": "https://example.com/report",
                "content_type": "text/plain",
                "status_code": 200,
                "headers": {},
                "redirect_chain": [],
                "checkpoint_before": {"page": 1},
                "checkpoint_after": {"page": 2},
            }, object_store=ObjectStore(str(tmp_path)))
            assert saved["checkpoint_after"] == {"page": 2}
            assert db.scalar(select(RawObject).where(RawObject.evidence_id == saved["evidence_id"])).watchlist_id == watchlist_id
        assert client.get("/api/v1/overview", headers={"Authorization": f"Bearer {owner_token}"}).json()["metrics"]["raw_evidence"] == 2
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def test_source_audit_retains_every_rss_entry(tmp_path, monkeypatch):
    class Response:
        status_code = 200
        body = b"home"
        final_url = "https://example.com"
        content_type = "text/html"

    entries = [{"entry_id": str(index), "title": f"Entry {index}", "url": f"https://example.com/{index}"} for index in range(7)]
    monkeypatch.setattr(audit_source_registry, "check_robots", lambda *_: (True, "CHECKED"))
    monkeypatch.setattr(audit_source_registry, "fetch_with_retry", lambda *_args, **_kwargs: Response())
    monkeypatch.setattr(audit_source_registry, "discover", lambda *_args, **_kwargs: [{"rss_url": "https://example.com/rss"}])
    monkeypatch.setattr(audit_source_registry, "collect_rss", lambda *_args, **_kwargs: {
        "body": b"feed", "status_code": 200, "entries": entries, "checkpoint_after": {},
    })
    result = audit_source_registry.audit_source({
        "id": "source", "name": "Source", "base_url": "https://example.com", "enabled": True,
        "allowed_domains": ["example.com"], "discover_rss": True,
    }, ObjectStore(str(tmp_path)), include_rss=True)
    assert result["feeds"][0]["entries"] == 7
    assert result["feeds"][0]["items"] == entries
