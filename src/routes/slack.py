"""
Slack Interactive Routes for the Tenant Access Request Service.

This module handles Slack interactive component callbacks (button clicks and modal submissions).
"""

import json
import logging
from urllib.parse import parse_qs

from fastapi import APIRouter, Header, Request, Response
from typing import Annotated

from src.service.app_state import get_app_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])


def _build_approval_modal(encoded_value: str, channel_id: str, message_ts: str) -> dict:
    """Build the modal view for entering KBase token."""
    return {
        "type": "modal",
        "callback_id": "approve_with_token",
        "private_metadata": json.dumps(
            {
                "encoded_value": encoded_value,
                "channel_id": channel_id,
                "message_ts": message_ts,
            }
        ),
        "title": {
            "type": "plain_text",
            "text": "Approve Access",
            "emoji": True,
        },
        "submit": {
            "type": "plain_text",
            "text": "Approve",
            "emoji": True,
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel",
            "emoji": True,
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Enter your KBase authentication token to approve this request.\n\nYour token is used once to add the user to the MinIO group and is not stored.",
                },
            },
            {
                "type": "input",
                "block_id": "token_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "kbase_token",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Paste your KBase token here",
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "KBase Token",
                    "emoji": True,
                },
            },
        ],
    }


@router.post(
    "/interact",
    include_in_schema=False,
    summary="Slack interactive callback",
    description="Handles Slack button clicks and modal submissions.",
)
async def slack_interact(
    request: Request,
    x_slack_signature: Annotated[str, Header()],
    x_slack_request_timestamp: Annotated[str, Header()],
):
    """
    Handle Slack interactive component callbacks.

    This endpoint handles:
    1. Button clicks (block_actions) - Opens a modal for token input
    2. Modal submissions (view_submission) - Processes the approval with the provided token
    """
    body = await request.body()
    app_state = get_app_state(request)
    slack_client = app_state.slack_client

    # Verify Slack signature
    slack_client.verify_slack_signature(
        signature=x_slack_signature,
        timestamp=x_slack_request_timestamp,
        body=body,
    )

    # Parse the payload
    parsed = parse_qs(body.decode("utf-8"))
    payload = json.loads(parsed["payload"][0])
    payload_type = payload.get("type")

    if payload_type == "block_actions":
        # Button was clicked
        return await _handle_button_click(payload, app_state)

    elif payload_type == "view_submission":
        # Modal was submitted
        return await _handle_modal_submission(payload, app_state)

    # Unknown payload type
    logger.warning(f"Unknown Slack payload type: {payload_type}")
    return Response(status_code=200)


async def _handle_button_click(payload: dict, app_state) -> Response:
    """Handle Approve/Deny button clicks."""
    action = payload["actions"][0]
    action_id = action["action_id"]
    encoded_value = action["value"]
    slack_user = payload["user"]["username"]
    channel_id = payload["channel"]["id"]
    message_ts = payload["message"]["ts"]
    trigger_id = payload["trigger_id"]

    slack_client = app_state.slack_client

    # Decode the request data
    request_data = slack_client._decode_request_data(encoded_value)
    requester = request_data["requester"]
    tenant_name = request_data["tenant_name"]

    if action_id == "approve_tenant_access":
        # Open modal to get admin's KBase token
        modal_view = _build_approval_modal(encoded_value, channel_id, message_ts)

        try:
            slack_client.client.views_open(
                trigger_id=trigger_id,
                view=modal_view,
            )
            logger.info(
                f"Opened approval modal for {slack_user} to approve {requester} → {tenant_name}"
            )
        except Exception as e:
            logger.error(f"Failed to open modal: {e}")
            # Fall back to pending message if modal fails
            permission = request_data["permission"]
            await slack_client.update_message_pending_approval(
                channel_id=channel_id,
                message_ts=message_ts,
                requester=requester,
                tenant_name=tenant_name,
                permission=permission,
                clicked_by=slack_user,
            )

    elif action_id == "deny_tenant_access":
        # Deny doesn't need a token - just update the message
        await slack_client.update_message_denied(
            channel_id=channel_id,
            message_ts=message_ts,
            requester=requester,
            tenant_name=tenant_name,
            denied_by=slack_user,
        )
        logger.info(f"Denied by Slack user {slack_user}: {requester} → {tenant_name}")

    # Slack expects a 200 response
    return Response(status_code=200)


async def _handle_modal_submission(payload: dict, app_state) -> Response:
    """Handle modal form submission with KBase token."""
    callback_id = payload["view"]["callback_id"]

    if callback_id != "approve_with_token":
        logger.warning(f"Unknown modal callback_id: {callback_id}")
        return Response(status_code=200)

    # Extract the token from the modal
    values = payload["view"]["state"]["values"]
    kbase_token = values["token_block"]["kbase_token"]["value"]

    # Extract metadata
    private_metadata = json.loads(payload["view"]["private_metadata"])
    encoded_value = private_metadata["encoded_value"]
    channel_id = private_metadata["channel_id"]
    message_ts = private_metadata["message_ts"]

    slack_user = payload["user"]["username"]
    slack_client = app_state.slack_client
    governance_client = app_state.governance_client

    # Decode the request data
    request_data = slack_client._decode_request_data(encoded_value)
    requester = request_data["requester"]
    tenant_name = request_data["tenant_name"]
    permission = request_data["permission"]

    try:
        # Call the governance API to add the user to the group
        read_only = permission == "read_only"
        await governance_client.add_group_member(
            admin_token=kbase_token,
            tenant_name=tenant_name,
            username=requester,
            read_only=read_only,
        )

        # Update the Slack message to show approval
        await slack_client.update_message_approved(
            channel_id=channel_id,
            message_ts=message_ts,
            requester=requester,
            tenant_name=tenant_name,
            permission=permission,
            approved_by=slack_user,
        )

        logger.info(
            f"Approved by {slack_user}: {requester} → {tenant_name} ({permission})"
        )

        # Return empty response to close the modal
        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Failed to approve access: {e}")

        # Return error to display in the modal
        return Response(
            status_code=200,
            content=json.dumps(
                {
                    "response_action": "errors",
                    "errors": {"token_block": f"Approval failed: {str(e)[:100]}"},
                }
            ),
            media_type="application/json",
        )
