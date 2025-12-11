"""Tests for the requests route."""

from unittest.mock import AsyncMock

from src.routes.requests import AccessRequestCreate


class TestCreateRequest:
    """Tests for POST /requests endpoint."""

    def test_create_request_success(self, test_client, sample_access_request, mock_app):
        """Test successful access request creation."""
        app, mock_state = mock_app
        mock_state.slack_client.send_access_request = AsyncMock(
            return_value={"message_ts": "1234567890.123456", "channel_id": "C12345"}
        )

        request_data = sample_access_request()
        response = test_client.post(
            "/requests/",
            json=request_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["tenant_name"] == request_data["tenant_name"]
        assert data["permission"] == request_data["permission"]

    def test_create_request_missing_tenant_name(self, test_client):
        """Test request fails without tenant_name."""
        response = test_client.post(
            "/requests/",
            json={"permission": "read_only"},
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422

    def test_create_request_invalid_permission(self, test_client):
        """Test request fails with invalid permission value."""
        response = test_client.post(
            "/requests/",
            json={"tenant_name": "test-tenant", "permission": "invalid"},
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422

    def test_create_request_read_write_permission(
        self, test_client, sample_access_request, mock_app
    ):
        """Test request with read_write permission."""
        app, mock_state = mock_app
        mock_state.slack_client.send_access_request = AsyncMock(
            return_value={"message_ts": "1234567890.123456", "channel_id": "C12345"}
        )

        request_data = sample_access_request(permission="read_write")
        response = test_client.post(
            "/requests/",
            json=request_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200
        assert response.json()["permission"] == "read_write"

    def test_create_request_with_justification(
        self, test_client, sample_access_request, mock_app
    ):
        """Test request with justification included."""
        app, mock_state = mock_app
        mock_state.slack_client.send_access_request = AsyncMock(
            return_value={"message_ts": "1234567890.123456", "channel_id": "C12345"}
        )

        request_data = sample_access_request(
            justification="Need access for quarterly analysis"
        )
        response = test_client.post(
            "/requests/",
            json=request_data,
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 200


class TestRequestModels:
    """Tests for request model validation."""

    def test_permission_enum_values(self):
        """Test that only valid permission values are accepted."""

        # Valid values
        request = AccessRequestCreate(tenant_name="test", permission="read_only")
        assert request.permission == "read_only"

        request = AccessRequestCreate(tenant_name="test", permission="read_write")
        assert request.permission == "read_write"

    def test_access_request_optional_justification(self):
        """Test that justification is optional."""

        request = AccessRequestCreate(tenant_name="test", permission="read_only")
        assert request.justification is None

        request = AccessRequestCreate(
            tenant_name="test", permission="read_only", justification="Testing"
        )
        assert request.justification == "Testing"
