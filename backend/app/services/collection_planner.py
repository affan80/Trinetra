from backend.app.services.source_registry import list_enabled

def plan(profile, sources):
    return [{"profile_id": profile["profile_id"], "source_id": str(source.id), "source_name": source.name, "adapter_name": source.adapter_name, "queries": profile.get("queries", []), "languages": profile.get("languages", []), "refresh_interval_seconds": profile["refresh_interval_seconds"]} for source in sources]

def build(profile, db): return plan(profile, list_enabled(db, profile.get("source_classes", [])))
