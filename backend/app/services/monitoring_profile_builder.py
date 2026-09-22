from datetime import datetime, timezone
from uuid import uuid4

def build(watchlist, requirement, queries, version: int) -> dict:
    return {"profile_id": str(uuid4()), "watchlist_id": str(watchlist.id), "version": version, "status": "ACTIVE", **requirement, "refresh_interval_seconds": watchlist.refresh_interval_minutes * 60, "queries": queries, "alert_rules": [{"type": r.type, "enabled": r.enabled, "threshold": r.threshold, "config": r.config} for r in watchlist.alert_rules], "generated_at": datetime.now(timezone.utc).isoformat()}
