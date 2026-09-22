import hashlib
from backend.app.dedup.contracts.fingerprint import FingerprintSet
from backend.app.dedup.fingerprints.text_normalizer import normalize_text_for_fingerprint

FINGERPRINT_VERSION = "fingerprint-v1"

def build(record) -> FingerprintSet:
    normalized = normalize_text_for_fingerprint(record.plain_text)
    return FingerprintSet(record.record_id, record.sha256, hashlib.sha256(normalized.encode("utf-8")).hexdigest(), FINGERPRINT_VERSION, record.primary_language)
