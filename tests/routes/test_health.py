"""Tests for the health route."""


def test_health_check(test_client):
    """Test the health check endpoint returns healthy status."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
