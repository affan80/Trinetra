import uuid
from datetime import datetime, timezone
from sqlalchemy import Enum, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.database import Base
from backend.app.db.models import Role # Oh, wait, I need to make sure I don't have circular imports.
# Role is defined in models.py. I need to move Role somewhere else if I split models.
