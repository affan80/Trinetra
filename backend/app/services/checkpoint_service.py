from sqlalchemy import select
from backend.app.db.models import SourceCheckpoint

def get(db, source_id):
    row = db.scalar(select(SourceCheckpoint).where(SourceCheckpoint.source_id == source_id))
    return row.cursor if row else {}

def save(db, source_id, cursor):
    row = db.scalar(select(SourceCheckpoint).where(SourceCheckpoint.source_id == source_id))
    if row: row.cursor = cursor
    else: db.add(SourceCheckpoint(source_id=source_id, cursor=cursor))
    db.commit()
