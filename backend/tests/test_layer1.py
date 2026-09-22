import os
os.environ["DATABASE_URL"] = "sqlite:///./test_layer1.db"
from fastapi.testclient import TestClient
from backend.app.main import app


def test_watchlist_compile_and_lifecycle():
    with TestClient(app) as client:
        token = client.post("/api/v1/auth/register", json={"email": "test@example.com", "password": "password123"}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        body = {"name": "Aerospace", "entities": [{"name": "Org-X", "type": "ORGANISATION", "aliases": ["OX"]}], "locations": [{"name": "Region-Y"}], "keywords": ["deployment"], "source_classes": ["NEWS"]}
        created = client.post("/api/v1/watchlists", json=body, headers=headers)
        assert created.status_code == 200
        watchlist_id = created.json()["id"]
        assert client.post(f"/api/v1/watchlists/{watchlist_id}/validate", headers=headers).status_code == 200
        profile = client.post(f"/api/v1/watchlists/{watchlist_id}/compile", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["version"] == 1
        assert profile.json()["queries"][0]["generated_from"]
        assert client.post(f"/api/v1/watchlists/{watchlist_id}/activate", headers=headers).status_code == 200
