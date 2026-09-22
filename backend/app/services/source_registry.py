from sqlalchemy import select
from backend.app.db.models import Source

def list_enabled(db, source_classes):
    return db.scalars(select(Source).where(Source.enabled.is_(True), Source.source_class.in_(source_classes))).all()

def safe_source(source):
    return {"id": str(source.id), "name": source.name, "source_class": source.source_class, "adapter_name": source.adapter_name, "allowed_domains": source.allowed_domains, "config": source.config}
