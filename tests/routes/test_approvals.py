"""Tests for the approvals route."""

from unittest.mock import AsyncMock

from src.routes.approvals import ApprovalRequest


class TestApproveRequest:
    """Tests for POST /approvals/approve endpoint."""

    def test_approve_request_success(
        self, admin_test_client, sample_approval_request, mock_app
    ):
        """Test successful approval by admin."""
        app, mock_state = mock_app
        mock_state.governance_client.add_group_member = AsyncMock(
            return_value={"status": "success"}
        )
        mock_state.slack_client.update_message_approved = AsyncMock()

        approval_data = sample_approval_request()
        response = admin_test_client.post(
            "/approvals/approve",
            json=approval_data,
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["requester"] == approval_data["requester"]
        assert data["tenant_name"] == approval_data["tenant_name"]

    def test_approve_request_missing_fields(self, admin_test_client):
        """Test approval fails with missing required fields."""
        response = admin_test_client.post(
            "/approvals/approve",
            json={"requester": "testuser"},
            headers={"Authorization": "Bearer admin_token"},
        )
        assert response.status_code == 422

    def test_approve_request_read_write_permission(
        self, admin_test_client, sample_approval_request, mock_app
    ):
        """Test approval with read_write permission."""
        app, mock_state = mock_app
        mock_state.governance_client.add_group_member = AsyncMock(
            return_value={"status": "success"}
        )
        mock_state.slack_client.update_message_approved = AsyncMock()

        approval_data = sample_approval_request(permission="read_write")
        response = admin_test_client.post(
            "/approvals/approve",
            json=approval_data,
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 200
        assert response.json()["permission"] == "read_write"


class TestDenyRequest:
    """Tests for POST /approvals/deny endpoint."""

    def test_deny_request_success(
        self, admin_test_client, sample_approval_request, mock_app
    ):
        """Test successful denial by admin."""
        app, mock_state = mock_app
        mock_state.slack_client.update_message_denied = AsyncMock()

        # Deny uses the same ApprovalRequest model
        denial_data = sample_approval_request()
        response = admin_test_client.post(
            "/approvals/deny",
            json=denial_data,
            headers={"Authorization": "Bearer admin_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "denied"


class TestApprovalModels:
    """Tests for approval model validation."""

    def test_approval_request_model(self):
        """Test ApprovalRequest model validation."""

        request = ApprovalRequest(
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_only",
            channel_id="C12345",
            message_ts="1234567890.123456",
        )
        assert request.requester == "testuser"
        assert request.tenant_name == "test-tenant"
        assert request.permission == "read_only"

    def test_approval_request_permissions(self):
        """Test that ApprovalRequest accepts both permission values."""

        # read_only
        request = ApprovalRequest(
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_only",
            channel_id="C12345",
            message_ts="1234567890.123456",
        )
        assert request.permission == "read_only"

        # read_write
        request = ApprovalRequest(
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_write",
            channel_id="C12345",
            message_ts="1234567890.123456",
        )
        assert request.permission == "read_write"
