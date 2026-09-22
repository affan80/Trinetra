def retry_delay(attempt: int, base_seconds: int = 60) -> int:
    return min(base_seconds * (2 ** max(0, attempt - 1)), 3600)

def should_retry(attempt: int, max_attempts: int, error_code: str | None = None) -> bool:
    return attempt < max_attempts and error_code not in {"SECURITY_REJECTED", "INVALID_JOB"}
