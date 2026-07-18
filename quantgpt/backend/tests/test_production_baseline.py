"""Production-surface smoke tests that do not require external services."""

from fastapi.testclient import TestClient

from app.main import app


def test_metrics_are_exposed_for_private_prometheus_scrape() -> None:
    response = TestClient(app).get("/metrics")
    assert response.status_code == 200
    assert b"quantgpt_http_requests_total" in response.content


def test_requests_receive_correlation_and_security_headers() -> None:
    response = TestClient(app).get("/api/v1/health", headers={"X-Request-ID": "release-test"})
    assert response.headers["x-request-id"] == "release-test"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
