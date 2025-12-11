"""
Slack client for sending approval request messages and handling callbacks.
"""

import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.service.exceptions import SlackError, SlackSignatureError

logger = logging.getLogger(__name__)


class SlackClient:
    """Client for interacting with Slack API."""

    def __init__(
        self,
        bot_token: str,
        signing_secret: str,
        channel_id: str,
    ):
        """
        Initialize the Slack client.

        Args:
            bot_token: Slack Bot OAuth Token (xoxb-...)
            signing_secret: Slack Signing Secret for request verification
            channel_id: Channel ID where approval messages are sent
        """
        self.client = WebClient(token=bot_token)
        self.signing_secret = signing_secret
        self.channel_id = channel_id

    def verify_slack_signature(
        self,
        signature: str,
        timestamp: str,
        body: bytes,
    ) -> bool:
        """
        Verify the Slack request signature.

        Args:
            signature: X-Slack-Signature header
            timestamp: X-Slack-Request-Timestamp header
            body: Raw request body

        Returns:
            True if signature is valid

        Raises:
            SlackSignatureError: If signature is invalid or request is too old
        """
        # Check timestamp to prevent replay attacks (5 min window)
        current_timestamp = int(time.time())
        if abs(current_timestamp - int(timestamp)) > 300:
            raise SlackSignatureError("Request timestamp is too old")

        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected_signature = (
            "v0="
            + hmac.new(
                self.signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        if not hmac.compare_digest(expected_signature, signature):
            raise SlackSignatureError("Invalid Slack signature")

        return True

    def _encode_request_data(
        self,
        requester: str,
        tenant_name: str,
        permission: str,
    ) -> str:
        """Encode request data for button value."""
        data = {
            "u": requester,  # user
            "t": tenant_name,  # tenant
            "p": "ro" if permission == "read_only" else "rw",  # permission
            "ts": int(time.time()),  # timestamp
        }
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

    def _decode_request_data(self, value: str) -> dict[str, Any]:
        """Decode request data from button value."""
        data = json.loads(base64.urlsafe_b64decode(value.encode()).decode())
        return {
            "requester": data["u"],
            "tenant_name": data["t"],
            "permission": "read_only" if data["p"] == "ro" else "read_write",
            "timestamp": data["ts"],
        }

    def _build_request_message_blocks(
        self,
        requester: str,
        tenant_name: str,
        permission: str,
        justification: str | None,
        encoded_data: str,
    ) -> list[dict]:
        """Build Slack Block Kit message for access request."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        permission_display = (
            "🔒 Read Only" if permission == "read_only" else "✏️ Read/Write"
        )

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔐 Tenant Access Request",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Requester:*\n{requester}"},
                    {"type": "mrkdwn", "text": f"*Tenant:*\n{tenant_name}"},
                    {"type": "mrkdwn", "text": f"*Permission:*\n{permission_display}"},
                    {"type": "mrkdwn", "text": f"*Requested:*\n{timestamp_str}"},
                ],
            },
        ]

        if justification:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Justification:*\n{justification}",
                    },
                }
            )

        # Add approve/deny buttons
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve",
                            "emoji": True,
                        },
                        "style": "primary",
                        "action_id": "approve_tenant_access",
                        "value": encoded_data,
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Deny",
                            "emoji": True,
                        },
                        "style": "danger",
                        "action_id": "deny_tenant_access",
                        "value": encoded_data,
                    },
                ],
            }
        )

        return blocks

    async def send_access_request(
        self,
        requester: str,
        tenant_name: str,
        permission: str,
        justification: str | None = None,
    ) -> dict:
        """
        Send an access request message to the Slack channel.

        Args:
            requester: Username of the person requesting access
            tenant_name: Name of the tenant to request access to
            permission: "read_only" or "read_write"
            justification: Optional justification for the request

        Returns:
            Dict with message_ts and channel_id
        """
        encoded_data = self._encode_request_data(requester, tenant_name, permission)
        blocks = self._build_request_message_blocks(
            requester, tenant_name, permission, justification, encoded_data
        )

        try:
            response = self.client.chat_postMessage(
                channel=self.channel_id,
                text=f"Tenant access request from {requester} for {tenant_name}",
                blocks=blocks,
            )
            logger.info(
                f"Sent access request to Slack: requester={requester}, tenant={tenant_name}"
            )
            return {
                "message_ts": response["ts"],
                "channel_id": response["channel"],
            }
        except SlackApiError as e:
            logger.error(f"Failed to send Slack message: {e}")
            raise SlackError(f"Failed to send Slack message: {e.response['error']}")

    async def update_message_approved(
        self,
        channel_id: str,
        message_ts: str,
        requester: str,
        tenant_name: str,
        permission: str,
        approved_by: str,
    ) -> None:
        """Update the Slack message to show it was approved."""
        permission_display = "Read Only" if permission == "read_only" else "Read/Write"
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Tenant Access Approved",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Requester:*\n{requester}"},
                    {"type": "mrkdwn", "text": f"*Tenant:*\n{tenant_name}"},
                    {"type": "mrkdwn", "text": f"*Permission:*\n{permission_display}"},
                    {"type": "mrkdwn", "text": f"*Approved by:*\n{approved_by}"},
                ],
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Approved at {timestamp_str}"},
                ],
            },
        ]

        try:
            self.client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"✅ Approved: {requester} → {tenant_name} ({permission_display})",
                blocks=blocks,
            )
        except SlackApiError as e:
            logger.warning(f"Failed to update Slack message: {e}")

    async def update_message_denied(
        self,
        channel_id: str,
        message_ts: str,
        requester: str,
        tenant_name: str,
        denied_by: str,
    ) -> None:
        """Update the Slack message to show it was denied."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "❌ Tenant Access Denied",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Requester:*\n{requester}"},
                    {"type": "mrkdwn", "text": f"*Tenant:*\n{tenant_name}"},
                    {"type": "mrkdwn", "text": f"*Denied by:*\n{denied_by}"},
                ],
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Denied at {timestamp_str}"},
                ],
            },
        ]

        try:
            self.client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"❌ Denied: {requester} → {tenant_name}",
                blocks=blocks,
            )
        except SlackApiError as e:
            logger.warning(f"Failed to update Slack message: {e}")

    async def update_message_pending_approval(
        self,
        channel_id: str,
        message_ts: str,
        requester: str,
        tenant_name: str,
        permission: str,
        clicked_by: str,
    ) -> None:
        """Update the Slack message to show approval is pending admin action."""
        permission_display = "Read Only" if permission == "read_only" else "Read/Write"
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⏳ Approval Pending Admin Action",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Requester:*\n{requester}"},
                    {"type": "mrkdwn", "text": f"*Tenant:*\n{tenant_name}"},
                    {"type": "mrkdwn", "text": f"*Permission:*\n{permission_display}"},
                    {"type": "mrkdwn", "text": f"*Clicked by:*\n{clicked_by}"},
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Awaiting admin API call at {timestamp_str}. "
                        f"Admin should call POST /approvals/approve with their KBase token.",
                    },
                ],
            },
        ]

        try:
            self.client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=f"⏳ Pending: {requester} → {tenant_name} ({permission_display})",
                blocks=blocks,
            )
        except SlackApiError as e:
            logger.warning(f"Failed to update Slack message: {e}")
