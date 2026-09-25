from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Verify health check endpoint returns 200 and healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "ProfitLens"
    assert "version" in data


def test_api_root():
    """Verify API root endpoint returns metadata and docs link."""
    response = client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "ProfitLens"
    assert data["docs"] == "/api/docs"
    assert data["health"] == "/api/health"
    assert "insights" in data["endpoints"]
    assert "reports" in data["endpoints"]


def test_openapi_schema_contains_all_modules():
    """Verify OpenAPI specification documents all platform router modules."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    paths = schema["paths"].keys()

    # Verify core platform modules are exposed in paths
    assert any(p.startswith("/api/auth") for p in paths)
    assert any(p.startswith("/api/datasets") for p in paths)
    assert any(p.startswith("/api/analytics") for p in paths)
    assert any(p.startswith("/api/ml") for p in paths)
    assert any(p.startswith("/api/insights") for p in paths)
    assert any(p.startswith("/api/reports") for p in paths)


def test_unauthorized_access_protection():
    """Verify protected endpoints reject requests lacking authentication."""
    # Attempting to fetch current user profile without JWT
    resp = client.get("/api/auth/me")
    assert resp.status_code in [401, 403]

    # Attempting to list datasets without JWT
    resp = client.get("/api/datasets")
    assert resp.status_code in [401, 403]

    # Attempting to generate reports without JWT
    resp = client.post("/api/reports/123/generate", json={"report_type": "executive_summary"})
    assert resp.status_code in [401, 403]
