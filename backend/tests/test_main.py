import os
from unittest.mock import AsyncMock, MagicMock

os.environ["ECHORA_BACKEND_TOKEN"] = "test-token"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.main import client as database_client


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(database_client, "create_rounds_table", AsyncMock())
    monkeypatch.setattr(database_client, "close", AsyncMock())
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_delete_round(client, monkeypatch):
    connection = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__.return_value = connection
    monkeypatch.setattr(
        database_client,
        "_get_pool",
        AsyncMock(return_value=pool),
    )

    r = client.delete("/api/rounds/123", headers={"x-echora-token": "test-token"})

    assert r.status_code == 204
    assert not r.content
    connection.execute.assert_awaited_once_with(
        "DELETE FROM public.rounds WHERE id = $1",
        "123",
    )


def test_create_round_returns_created_status(client, monkeypatch):
    monkeypatch.setattr(database_client, "exists", AsyncMock(return_value=False))
    ingest = AsyncMock()
    monkeypatch.setattr(database_client, "ingest", ingest)
    payload = {
        "id": "round-1",
        "participantId": "P01",
        "mode": "echora",
        "objectLabel": "mug",
        "durationSeconds": 5.5,
        "success": True,
        "isPractice": False,
        "headTrackingUsed": True,
        "placement": "lidarDepth",
        "startedAt": "2026-10-10T18:22:05Z",
        "appVersion": "0.1.0",
    }

    response = client.post(
        "/api/rounds",
        json=payload,
        headers={"x-echora-token": "test-token"},
    )

    assert response.status_code == 201
    assert response.json() == {"id": "round-1", "status": "created"}
    ingest.assert_awaited_once()


def sighting_payload(**overrides):
    payload = {
        "id": "sighting-1",
        "participantId": "P01",
        "objectLabel": "blue mug",
        "utterance": "where's my mug",
        "seenAt": "2026-10-10T18:20:41Z",
        "x": 0.25,
        "y": -0.25,
        "z": -0.55,
        "placement": "lidarDepth",
        "confidence": 0.92,
    }
    payload.update(overrides)
    return payload


def test_create_sighting_returns_created_status(client, monkeypatch):
    monkeypatch.setattr(database_client, "sighting_exists", AsyncMock(return_value=False))
    ingest = AsyncMock()
    monkeypatch.setattr(database_client, "ingest_sighting", ingest)

    response = client.post(
        "/api/sightings",
        json=sighting_payload(),
        headers={"x-echora-token": "test-token"},
    )

    assert response.status_code == 201
    assert response.json() == {"id": "sighting-1", "status": "created"}
    ingest.assert_awaited_once()
    row = ingest.await_args.args[0]
    assert row["utterance"] == "where's my mug"
    assert row["placement"] == "lidarDepth"


def test_create_sighting_is_idempotent(client, monkeypatch):
    monkeypatch.setattr(database_client, "sighting_exists", AsyncMock(return_value=True))
    ingest = AsyncMock()
    monkeypatch.setattr(database_client, "ingest_sighting", ingest)

    response = client.post(
        "/api/sightings",
        json=sighting_payload(),
        headers={"x-echora-token": "test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": "sighting-1", "status": "exists"}
    ingest.assert_not_awaited()


def test_create_sighting_rejects_bad_token(client):
    response = client.post(
        "/api/sightings",
        json=sighting_payload(),
        headers={"x-echora-token": "wrong-token"},
    )

    assert response.status_code == 401


def test_list_sightings_returns_newest_first(client, monkeypatch):
    rows = [
        sighting_payload(id="new", seenAt="2026-10-10T18:25:00Z"),
        sighting_payload(id="old", seenAt="2026-10-10T18:20:00Z"),
    ]
    monkeypatch.setattr(database_client, "list_sightings", AsyncMock(return_value=rows))

    response = client.get("/api/sightings?limit=20")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == ["new", "old"]
