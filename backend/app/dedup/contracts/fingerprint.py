from dataclasses import dataclass

@dataclass(frozen=True)
class FingerprintSet:
    record_id: str
    raw_sha256: str | None
    normalized_text_hash: str
    fingerprint_version: str
    language: str | None

@dataclass(frozen=True)
class QualityResult:
    status: str
    score: float
    version: str
    components: dict
    flags: list[str]
