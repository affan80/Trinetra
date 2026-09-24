import uuid
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from backend.app.db.database import Base
from backend.app.db.seed import seed_database_if_empty, seed_user_watchlist
from backend.app.db.models import Watchlist, CanonicalRecord, Location, Source, User, Role
from backend.app.services.overview import build_incident, build_overview

def test_database_seeder():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_database_if_empty(db)
        sources = list(db.scalars(select(Source)))
        assert len(sources) >= 1

        user = User(id=uuid.uuid4(), email="analyst@example.com", password_hash="hash", role=Role.ANALYST)
        db.add(user)
        db.commit()

        seed_user_watchlist(db, user)
        watchlists = list(db.scalars(select(Watchlist)))
        records = list(db.scalars(select(CanonicalRecord)))
        locations = list(db.scalars(select(Location)))

        assert len(watchlists) >= 1
        assert len(records) >= 1
        assert len(locations) >= 1
        assert build_overview(db, user)["records"][0]["demo"] is True
        incident_record = build_incident(db, watchlists[0])["records"][0]
        assert incident_record["demo"] is True
        assert incident_record["url"] is None
        for loc in locations:
            assert loc.latitude is not None
            assert loc.longitude is not None
