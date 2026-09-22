from backend.app.dedup.contracts.fingerprint import QualityResult
from backend.app.dedup.quality.rules import ERROR_PATTERNS, QUALITY_VERSION

def validate(record) -> QualityResult:
    text = (record.plain_text or "").strip(); lowered = text.lower(); flags = []
    processing = record.processing_quality or {}
    if not text: return QualityResult("EMPTY", 0.0, QUALITY_VERSION, {"text": 0.0}, ["empty_text"])
    if any(pattern in lowered for pattern in ERROR_PATTERNS): flags.append("known_error_page")
    if len(text) < 120: flags.append("short_text")
    if not record.title: flags.append("missing_title")
    if processing.get("status") in {"ERROR", "CORRUPT"}: flags.append("parser_error")
    status = "ERROR_PAGE" if "known_error_page" in flags else "LOW_CONTENT" if len(text) < 120 else "PARTIAL" if processing.get("status") not in {None, "COMPLETE"} else "VALID"
    return QualityResult(status, score(record, flags), QUALITY_VERSION, components(record, flags), flags)

def components(record, flags):
    text = (record.plain_text or "").strip()
    return {"text": min(1.0, len(text) / 2000), "metadata": sum(bool(x) for x in (record.title, record.canonical_url, record.evidence_id, record.source_id)) / 4, "language": 1.0 if record.primary_language else 0.0, "timestamp": 1.0 if record.published_at or record.retrieved_at else 0.0, "parser": 1.0 if (record.processing_quality or {}).get("status", "COMPLETE") == "COMPLETE" else 0.5}

def score(record, flags):
    values = components(record, flags); weighted = {"text": .30, "metadata": .15, "language": .15, "timestamp": .10, "parser": .10, "usable": .20}; usable = 0.0 if "known_error_page" in flags else min(1.0, len((record.plain_text or "").strip()) / 500); values["usable"] = usable
    return round(sum(values[key] * weight for key, weight in weighted.items()), 4)
