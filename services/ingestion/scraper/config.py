import os


def env_bool(name, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


class ScraplingSettings:
    parser_enabled = env_bool("SCRAPLING_PARSER_ENABLED", True)
    fetch_fallback_enabled = env_bool("SCRAPLING_FETCH_FALLBACK_ENABLED", False)
    fetch_mode = os.getenv("SCRAPLING_FETCH_MODE", "static").strip().lower()
    browser_enabled = env_bool("SCRAPLING_BROWSER_ENABLED", False)
    adaptive_enabled = env_bool("SCRAPLING_ADAPTIVE_ENABLED", False)
    timeout_ms = env_int("SCRAPLING_TIMEOUT_MS", 30000)
    proxy_url = os.getenv("SCRAPLING_PROXY_URL", "").strip()


def get_scrapling_settings():
    return ScraplingSettings()
