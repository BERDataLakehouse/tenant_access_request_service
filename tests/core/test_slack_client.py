"""Tests for the SlackClient."""

import hashlib
import hmac
import time

import pytest
from unittest.mock import patch
from slack_sdk.errors import SlackApiError

from src.core.slack_client import SlackClient
from src.service.exceptions import SlackError, SlackSignatureError


class TestSlackSignatureVerification:
    """Tests for Slack signature verification."""

    def test_verify_valid_signature(self, mock_slack_client):
        """Test verification of a valid Slack signature."""
        timestamp = str(int(time.time()))
        body = b"test_body"

        # Generate a valid signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected_signature = (
            "v0="
            + hmac.new(
                mock_slack_client.signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        result = mock_slack_client.verify_slack_signature(
            expected_signature, timestamp, body
        )
        assert result is True

    def test_verify_invalid_signature(self, mock_slack_client):
        """Test rejection of invalid Slack signature."""
        timestamp = str(int(time.time()))
        body = b"test_body"

        with pytest.raises(SlackSignatureError):
            mock_slack_client.verify_slack_signature(
                "v0=invalid_signature", timestamp, body
            )

    def test_verify_old_timestamp(self, mock_slack_client):
        """Test rejection of requests with old timestamps."""
        old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
        body = b"test_body"

        with pytest.raises(SlackSignatureError, match="timestamp is too old"):
            mock_slack_client.verify_slack_signature(
                "v0=any_signature", old_timestamp, body
            )


class TestRequestDataEncoding:
    """Tests for request data encoding/decoding."""

    def test_encode_decode_request_data(self, mock_slack_client):
        """Test encoding and decoding of request data."""
        requester = "testuser"
        tenant_name = "test-tenant"
        permission = "read_only"

        # Encode
        encoded = mock_slack_client._encode_request_data(
            requester, tenant_name, permission
        )
        assert isinstance(encoded, str)

        # Decode
        decoded = mock_slack_client._decode_request_data(encoded)
        assert decoded["requester"] == requester
        assert decoded["tenant_name"] == tenant_name
        assert decoded["permission"] == permission
        assert "timestamp" in decoded

    def test_encode_read_write_permission(self, mock_slack_client):
        """Test encoding read_write permission."""
        encoded = mock_slack_client._encode_request_data(
            "testuser", "test-tenant", "read_write"
        )
        decoded = mock_slack_client._decode_request_data(encoded)
        assert decoded["permission"] == "read_write"


class TestSendAccessRequest:
    """Tests for sending access request messages."""

    @pytest.mark.asyncio
    async def test_send_access_request_success(self, mock_slack_client):
        """Test successful access request message sending."""
        result = await mock_slack_client.send_access_request(
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_only",
            justification="Need access for testing",
        )

        assert "message_ts" in result
        assert "channel_id" in result
        mock_slack_client.client.chat_postMessage.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_access_request_no_justification(self, mock_slack_client):
        """Test sending request without justification."""
        result = await mock_slack_client.send_access_request(
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_only",
        )

        assert "message_ts" in result
        mock_slack_client.client.chat_postMessage.assert_called_once()


class TestUpdateMessages:
    """Tests for message update methods."""

    @pytest.mark.asyncio
    async def test_update_message_approved(self, mock_slack_client):
        """Test updating message to approved state."""
        await mock_slack_client.update_message_approved(
            channel_id="C12345",
            message_ts="1234567890.123456",
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_only",
            approved_by="adminuser",
        )

        mock_slack_client.client.chat_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_message_denied(self, mock_slack_client):
        """Test updating message to denied state."""
        await mock_slack_client.update_message_denied(
            channel_id="C12345",
            message_ts="1234567890.123456",
            requester="testuser",
            tenant_name="test-tenant",
            denied_by="adminuser",
        )

        mock_slack_client.client.chat_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_message_pending_approval(self, mock_slack_client):
        """Test updating message to pending admin action state."""
        await mock_slack_client.update_message_pending_approval(
            channel_id="C12345",
            message_ts="1234567890.123456",
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_only",
            clicked_by="adminuser",
        )

        mock_slack_client.client.chat_update.assert_called_once()


class TestMessageBlockBuilding:
    """Tests for Slack Block Kit message building."""

    def test_build_request_message_blocks(self, mock_slack_client):
        """Test building access request message blocks."""
        encoded_data = mock_slack_client._encode_request_data(
            "testuser", "test-tenant", "read_only"
        )

        blocks = mock_slack_client._build_request_message_blocks(
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_only",
            justification="Testing",
            encoded_data=encoded_data,
        )

        assert isinstance(blocks, list)
        assert len(blocks) >= 3  # Header, section, actions at minimum

        # Check for header block
        header_block = blocks[0]
        assert header_block["type"] == "header"

        # Check for actions block with buttons
        actions_block = [b for b in blocks if b["type"] == "actions"][0]
        assert len(actions_block["elements"]) == 2  # Approve and Deny buttons

    def test_build_request_message_without_justification(self, mock_slack_client):
        """Test building message blocks without justification."""
        encoded_data = mock_slack_client._encode_request_data(
            "testuser", "test-tenant", "read_only"
        )

        blocks = mock_slack_client._build_request_message_blocks(
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_only",
            justification=None,
            encoded_data=encoded_data,
        )

        # Should not have justification section
        justification_blocks = [
            b
            for b in blocks
            if b.get("type") == "section" and "Justification" in str(b)
        ]
        assert len(justification_blocks) == 0


class TestSlackClientInit:
    """Tests for SlackClient initialization."""

    def test_init_stores_config(self):
        """Test that initialization stores configuration correctly."""
        with patch("src.core.slack_client.WebClient") as mock_web_client:
            client = SlackClient(
                bot_token="xoxb-test-token",
                signing_secret="test_secret",
                channel_id="C12345",
            )

            assert client.signing_secret == "test_secret"
            assert client.channel_id == "C12345"
            mock_web_client.assert_called_once_with(token="xoxb-test-token")


class TestSlackApiErrors:
    """Tests for SlackApiError handling."""

    @pytest.mark.asyncio
    async def test_send_access_request_slack_error(self, mock_slack_client):
        """Test that SlackApiError is caught and re-raised as SlackError."""
        mock_slack_client.client.chat_postMessage.side_effect = SlackApiError(
            message="channel_not_found",
            response={"error": "channel_not_found"},
        )

        with pytest.raises(SlackError, match="Failed to send Slack message"):
            await mock_slack_client.send_access_request(
                requester="testuser",
                tenant_name="test-tenant",
                permission="read_only",
            )

    @pytest.mark.asyncio
    async def test_update_message_approved_handles_error(self, mock_slack_client):
        """Test that update_message_approved logs but doesn't raise on error."""
        mock_slack_client.client.chat_update.side_effect = SlackApiError(
            message="message_not_found",
            response={"error": "message_not_found"},
        )

        # Should not raise - just logs warning
        await mock_slack_client.update_message_approved(
            channel_id="C12345",
            message_ts="1234567890.123456",
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_only",
            approved_by="adminuser",
        )

    @pytest.mark.asyncio
    async def test_update_message_denied_handles_error(self, mock_slack_client):
        """Test that update_message_denied logs but doesn't raise on error."""
        mock_slack_client.client.chat_update.side_effect = SlackApiError(
            message="message_not_found",
            response={"error": "message_not_found"},
        )

        # Should not raise - just logs warning
        await mock_slack_client.update_message_denied(
            channel_id="C12345",
            message_ts="1234567890.123456",
            requester="testuser",
            tenant_name="test-tenant",
            denied_by="adminuser",
        )

    @pytest.mark.asyncio
    async def test_update_message_pending_handles_error(self, mock_slack_client):
        """Test that update_message_pending_approval logs but doesn't raise on error."""
        mock_slack_client.client.chat_update.side_effect = SlackApiError(
            message="message_not_found",
            response={"error": "message_not_found"},
        )

        # Should not raise - just logs warning
        await mock_slack_client.update_message_pending_approval(
            channel_id="C12345",
            message_ts="1234567890.123456",
            requester="testuser",
            tenant_name="test-tenant",
            permission="read_only",
            clicked_by="adminuser",
        )
