from sqlalchemy import select
from backend.app.db.models import AuditLog, CanonicalRecord, DuplicateCluster, DuplicateClusterMember, DuplicateType, RecordFingerprint, RecordQuality, RecordSimilarity
from backend.app.dedup.clusters.cluster_service import DECISION_VERSION, assign, find_cluster
from backend.app.dedup.fingerprints.exact_hash import build
from backend.app.dedup.quality.validator import validate

def process(db, record_id: str, actor_id=None) -> dict:
    record = db.scalar(select(CanonicalRecord).where(CanonicalRecord.record_id == record_id))
    if not record: raise ValueError("canonical record not found")
    quality = validate(record); _upsert_quality(db, record.record_id, quality)
    fingerprint = build(record); stored = _upsert_fingerprint(db, fingerprint)
    existing = _exact_candidate(db, record, fingerprint)
    if existing:
        cluster = find_cluster(db, existing.record_id)
        relationship = DuplicateType.EXACT_RAW.value if fingerprint.raw_sha256 and fingerprint.raw_sha256 == existing.sha256 else DuplicateType.EXACT_TEXT.value
        cluster = assign(db, record, relationship, 1.0, "exact_hash", {"raw_hash_match": relationship == DuplicateType.EXACT_RAW.value, "normalized_text_hash_match": True}, cluster)
        result = _annotation(record, quality, fingerprint, cluster, relationship, False)
    else:
        changed_url = _same_url_changed_content(db, record)
        if changed_url: _similarity(db, record.record_id, changed_url.record_id, DuplicateType.DOCUMENT_VERSION.value, {"canonical_url_match": True}, 1.0)
        cluster = assign(db, record, "ORIGINAL", 1.0, "new_cluster", {"reason": "no exact raw or normalized text match"})
        result = _annotation(record, quality, fingerprint, cluster, "ORIGINAL", True)
    db.commit()
    if actor_id: db.add(AuditLog(event_type="DUPLICATE_DETECTED", user_id=actor_id, new_value={"record_id": record_id, "cluster_id": str(result["cluster_id"]), "relationship": result["relationship"]})); db.commit()
    return result

def _upsert_quality(db, record_id, result):
    row = db.scalar(select(RecordQuality).where(RecordQuality.record_id == record_id))
    values = {"status": result.status, "quality_score": result.score, "quality_version": result.version, "components": result.components, "flags": result.flags}
    if row:
        for key, value in values.items(): setattr(row, key, value)
    else: db.add(RecordQuality(record_id=record_id, **values))

def _upsert_fingerprint(db, value):
    row = db.scalar(select(RecordFingerprint).where(RecordFingerprint.record_id == value.record_id))
    values = {"raw_sha256": value.raw_sha256, "normalized_text_hash": value.normalized_text_hash, "language": value.language, "fingerprint_version": value.fingerprint_version}
    if row:
        for key, item in values.items(): setattr(row, key, item)
    else: row = RecordFingerprint(record_id=value.record_id, **values); db.add(row)
    db.flush(); return row

def _exact_candidate(db, record, fingerprint):
    if fingerprint.raw_sha256:
        raw = select(CanonicalRecord).join(RecordFingerprint, RecordFingerprint.record_id == CanonicalRecord.record_id).where(CanonicalRecord.record_id != record.record_id, RecordFingerprint.raw_sha256 == fingerprint.raw_sha256).order_by(CanonicalRecord.created_at)
        if candidate := db.scalar(raw): return candidate
    text = select(CanonicalRecord).join(RecordFingerprint, RecordFingerprint.record_id == CanonicalRecord.record_id).where(CanonicalRecord.record_id != record.record_id, RecordFingerprint.normalized_text_hash == fingerprint.normalized_text_hash).order_by(CanonicalRecord.created_at)
    return db.scalar(text)

def _same_url_changed_content(db, record):
    if not record.canonical_url: return None
    return db.scalar(select(CanonicalRecord).where(CanonicalRecord.record_id != record.record_id, CanonicalRecord.canonical_url == record.canonical_url, CanonicalRecord.sha256 != record.sha256).order_by(CanonicalRecord.created_at))

def _similarity(db, a, b, decision, signals, score):
    low, high = sorted((a, b)); exists = db.scalar(select(RecordSimilarity).where(RecordSimilarity.record_a_id == low, RecordSimilarity.record_b_id == high, RecordSimilarity.decision_version == DECISION_VERSION))
    if not exists: db.add(RecordSimilarity(record_a_id=low, record_b_id=high, similarity_type=decision, similarity_score=score, signals=signals, decision=decision, decision_version=DECISION_VERSION))

def _annotation(record, quality, fingerprint, cluster, relationship, independent):
    return {"record_id": record.record_id, "quality_status": quality.status, "quality_score": quality.score, "cluster_id": str(cluster.id), "duplicate_relationship": relationship, "representative_record_id": cluster.representative_record_id, "representative": cluster.representative_record_id == record.record_id, "independent_observation": independent, "processing_versions": {"quality": quality.version, "dedup": DECISION_VERSION, "fingerprint": fingerprint.fingerprint_version}}
