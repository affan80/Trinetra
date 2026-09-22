import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:////tmp/trinetra-layer5-test.db"
Path("/tmp/trinetra-layer5-test.db").unlink(missing_ok=True)

from backend.app.db.database import Base, engine, SessionLocal
from backend.app.db.models import CanonicalRecord, RecordSimilarity
from backend.app.dedup.services.dedup_pipeline import process

Base.metadata.create_all(engine)

def record(record_id, text, raw, url="https://example.com/a", title="Example"):
    return CanonicalRecord(record_id=record_id, evidence_id=f"EV-{record_id}", record_type="ARTICLE", canonical_url=url, title=title, plain_text=text, primary_language="en", retrieved_at=datetime.now(timezone.utc), sha256=raw, processing_quality={"status": "COMPLETE"})

def test_exact_raw_text_url_version_and_idempotency():
    with SessionLocal() as db:
        prefix = uuid.uuid4().hex[:8]
        ids = [f"{prefix}-{i}" for i in range(1, 6)]
        base_text = f"{prefix} Company X announced acquisition of Company Y."
        original = record(ids[0], base_text, f"{prefix}-raw-a", f"https://example.com/{prefix}")
        raw_copy = record(ids[1], "different canonical text is preserved", f"{prefix}-raw-a", f"https://example.com/{prefix}/b")
        text_copy = record(ids[2], f"  {prefix}   Company   X announced acquisition of Company Y. ", f"{prefix}-raw-c", f"https://example.com/{prefix}/c")
        changed = record(ids[3], f"{prefix} Company X cancelled acquisition of Company Y.", f"{prefix}-raw-d", f"https://example.com/{prefix}")
        unique = record(ids[4], f"{prefix} A separate weather report with unrelated content.", f"{prefix}-raw-e", f"https://example.com/{prefix}/e")
        db.add_all([original, raw_copy, text_copy, changed, unique]); db.commit()
        first = process(db, ids[0]); assert first["duplicate_relationship"] == "ORIGINAL" and first["representative"]
        second = process(db, ids[1]); assert second["duplicate_relationship"] == "EXACT_RAW" and not second["independent_observation"]
        third = process(db, ids[2]); assert third["duplicate_relationship"] == "EXACT_TEXT"
        changed_result = process(db, ids[3]); assert changed_result["duplicate_relationship"] == "ORIGINAL"
        assert db.query(RecordSimilarity).filter_by(record_a_id=ids[0], record_b_id=ids[3]).one().decision == "DOCUMENT_VERSION"
        unique_result = process(db, ids[4]); assert unique_result["representative"]
        again = process(db, ids[2]); assert again["cluster_id"] == third["cluster_id"]
        assert db.query(RecordSimilarity).filter(RecordSimilarity.record_a_id.in_(ids), RecordSimilarity.record_b_id.in_(ids)).count() == 1
