import os
import uuid
os.environ["TESTING"] = "true"
from fastapi.testclient import TestClient
from backend.app.main import app

def test_non_owner_cannot_read_watchlist():
    with TestClient(app) as client:
        suffix = uuid.uuid4().hex
        owner = client.post("/api/v1/auth/register", json={"email": f"owner-{suffix}@example.com", "password": "password123"}).json()["access_token"]
        other = client.post("/api/v1/auth/register", json={"email": f"other-{suffix}@example.com", "password": "password123"}).json()["access_token"]
        created = client.post("/api/v1/watchlists", headers={"Authorization": f"Bearer {owner}"}, json={"name": f"private-{suffix}"})
        assert created.status_code == 200
        watchlist_id = created.json()["id"]
        assert client.get(f"/api/v1/watchlists/{watchlist_id}", headers={"Authorization": f"Bearer {other}"}).status_code == 404
