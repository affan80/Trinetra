import uuid
from datetime import datetime, timezone
from backend.app.db.models import CollectionProvenance, RawObject
from backend.app.security.http_client import sha256

def preserve(db, job, source, result, *, object_store, collector_version="layer3-v0.1"):
    value = result if isinstance(result, dict) else result.__dict__
    digest = sha256(value["body"]); uri = object_store.put(value["body"], digest)
    evidence = RawObject(evidence_id="EV-" + uuid.uuid4().hex[:12].upper(), job_id=job.id, source_id=source.id, source_url=value["requested_url"], final_url=value["final_url"], adapter_type="RSS", object_uri=uri, sha256=digest, content_type=value["content_type"], content_length=len(value["body"]), http_status=value["status_code"], etag=value["headers"].get("etag"), last_modified=value["headers"].get("last-modified"), collector_version=collector_version)
    db.add(evidence); db.flush()
    provenance = CollectionProvenance(raw_object_id=evidence.id, job_id=job.id, source_id=source.id, collector_id="trinetra-layer3", collector_version=collector_version, adapter_type="RSS", requested_url=value["requested_url"], final_url=value["final_url"], redirect_chain=value["redirect_chain"], http_headers_sanitized=value["headers"], collection_method="rss", checkpoint_before=value["checkpoint_before"], checkpoint_after=value["checkpoint_after"])
    db.add(provenance); db.commit(); return {"evidence_id": evidence.evidence_id, "raw_object_uri": uri, "sha256": digest, "provenance_id": str(provenance.id), "checkpoint_before": result.checkpoint_before, "checkpoint_after": result.checkpoint_after}
