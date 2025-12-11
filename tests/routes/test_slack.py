"""Tests for the Slack interactive callback route."""

from unittest.mock import AsyncMock, MagicMock
import json
import time
import hmac
import hashlib


class TestSlackInteract:
    """Tests for POST /slack/interact endpoint."""

    def _generate_slack_signature(
        self, body: str, timestamp: str, signing_secret: str
    ) -> str:
        """Generate a valid Slack signature for testing."""
        sig_basestring = f"v0:{timestamp}:{body}"
        return (
            "v0="
            + hmac.new(
                signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

    def test_slack_interact_approve_action(self, test_client, mock_app):
        """Test handling approve button click from Slack - opens modal."""
        app, mock_state = mock_app
        mock_state.slack_client.update_message_pending_approval = AsyncMock()
        mock_state.slack_client.verify_slack_signature = lambda *args, **kwargs: True
        mock_state.slack_client._decode_request_data = lambda v: {
            "requester": "testuser",
            "tenant_name": "test-tenant",
            "permission": "read_only",
            "timestamp": 1700000000,
        }
        # Mock the Slack WebClient's views_open
        mock_state.slack_client.client = MagicMock()
        mock_state.slack_client.client.views_open = MagicMock(return_value={"ok": True})

        timestamp = str(int(time.time()))
        payload = {
            "type": "block_actions",
            "user": {"id": "U12345", "username": "adminuser"},
            "channel": {"id": "C12345"},
            "message": {"ts": "1234567890.123456"},
            "trigger_id": "1234567890.12345678",
            "actions": [
                {
                    "action_id": "approve_tenant_access",
                    "value": "eyJ1IjogInRlc3R1c2VyIiwgInQiOiAidGVzdC10ZW5hbnQiLCAicCI6ICJybyIsICJ0cyI6IDE3MDAwMDAwMDB9",
                }
            ],
        }
        body = f"payload={json.dumps(payload)}"

        response = test_client.post(
            "/slack/interact",
            content=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Slack-Signature": "v0=test",
                "X-Slack-Request-Timestamp": timestamp,
            },
        )

        # Should return 200 OK (empty response to Slack)
        assert response.status_code == 200
        # Verify views_open was called
        mock_state.slack_client.client.views_open.assert_called_once()

    def test_slack_interact_deny_action(self, test_client, mock_app):
        """Test handling deny button click from Slack."""
        app, mock_state = mock_app
        mock_state.slack_client.update_message_denied = AsyncMock()
        mock_state.slack_client.verify_slack_signature = lambda *args, **kwargs: True
        mock_state.slack_client._decode_request_data = lambda v: {
            "requester": "testuser",
            "tenant_name": "test-tenant",
            "permission": "read_only",
            "timestamp": 1700000000,
        }

        timestamp = str(int(time.time()))
        payload = {
            "type": "block_actions",
            "user": {"id": "U12345", "username": "adminuser"},
            "channel": {"id": "C12345"},
            "message": {"ts": "1234567890.123456"},
            "trigger_id": "1234567890.12345678",
            "actions": [
                {
                    "action_id": "deny_tenant_access",
                    "value": "eyJ1IjogInRlc3R1c2VyIiwgInQiOiAidGVzdC10ZW5hbnQiLCAicCI6ICJybyIsICJ0cyI6IDE3MDAwMDAwMDB9",
                }
            ],
        }
        body = f"payload={json.dumps(payload)}"

        response = test_client.post(
            "/slack/interact",
            content=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Slack-Signature": "v0=test",
                "X-Slack-Request-Timestamp": timestamp,
            },
        )

        assert response.status_code == 200
        # Verify message was updated to denied
        mock_state.slack_client.update_message_denied.assert_called_once()

    def test_slack_interact_modal_submission(self, test_client, mock_app):
        """Test handling modal submission with KBase token."""
        app, mock_state = mock_app
        mock_state.slack_client.verify_slack_signature = lambda *args, **kwargs: True
        mock_state.slack_client._decode_request_data = lambda v: {
            "requester": "testuser",
            "tenant_name": "test-tenant",
            "permission": "read_only",
            "timestamp": 1700000000,
        }
        mock_state.slack_client.update_message_approved = AsyncMock()
        mock_state.governance_client.add_group_member = AsyncMock()

        timestamp = str(int(time.time()))
        payload = {
            "type": "view_submission",
            "user": {"id": "U12345", "username": "adminuser"},
            "view": {
                "callback_id": "approve_with_token",
                "private_metadata": json.dumps(
                    {
                        "encoded_value": "test_encoded",
                        "channel_id": "C12345",
                        "message_ts": "1234567890.123456",
                    }
                ),
                "state": {
                    "values": {
                        "token_block": {"kbase_token": {"value": "TEST_KBASE_TOKEN"}}
                    }
                },
            },
        }
        body = f"payload={json.dumps(payload)}"

        response = test_client.post(
            "/slack/interact",
            content=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Slack-Signature": "v0=test",
                "X-Slack-Request-Timestamp": timestamp,
            },
        )

        assert response.status_code == 200
        # Verify governance API was called with the token
        mock_state.governance_client.add_group_member.assert_called_once()
        # Verify message was approved
        mock_state.slack_client.update_message_approved.assert_called_once()

    def test_slack_interact_missing_headers(self, test_client):
        """Test rejection of requests without Slack headers."""
        payload = {"type": "block_actions", "actions": []}
        body = f"payload={json.dumps(payload)}"

        response = test_client.post(
            "/slack/interact",
            content=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Should fail due to missing headers
        assert response.status_code in [400, 401, 422]
