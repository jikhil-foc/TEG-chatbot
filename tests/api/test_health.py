"""Smoke tests for the application wiring and health endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_echo(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"message": "hi"})
    assert response.status_code == 200
    assert response.json() == {"reply": "Echo: hi"}
