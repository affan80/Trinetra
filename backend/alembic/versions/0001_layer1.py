"""Layer 1 schema."""
from alembic import op
from backend.app.db.base import Base
from backend.app.db.database import engine
revision = "0001_layer1"; down_revision = None; branch_labels = None; depends_on = None
def upgrade(): Base.metadata.create_all(engine)
def downgrade(): Base.metadata.drop_all(engine)
