"""
Approval Routes for the Tenant Access Request Service.

This module provides endpoints for admins to approve or deny tenant access requests.
These are admin-only endpoints that require CDM_JUPYTERHUB_ADMIN role.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field

from src.service.app_state import get_app_state
from src.service.dependencies import require_admin
from src.service.kb_auth import KBaseUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["approvals"])


# ===== RESPONSE MODELS =====


class ApprovalRequest(BaseModel):
    """Request body for approval/denial."""

    model_config = ConfigDict(str_strip_whitespace=True)

    requester: Annotated[
        str, Field(description="Username who requested access", min_length=1)
    ]
    tenant_name: Annotated[
        str, Field(description="Tenant name to grant access to", min_length=1)
    ]
    permission: Annotated[
        Literal["read_only", "read_write"],
        Field(description="Permission level to grant"),
    ]
    channel_id: Annotated[
        str,
        Field(description="Slack channel ID where the request message was posted"),
    ]
    message_ts: Annotated[
        str,
        Field(description="Slack message timestamp to update"),
    ]


class ApprovalResponse(BaseModel):
    """Response for approval operations."""

    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    status: Annotated[str, Field(description="Result status: approved or denied")]
    requester: Annotated[str, Field(description="Username who was approved/denied")]
    tenant_name: Annotated[str, Field(description="Tenant name")]
    permission: Annotated[str, Field(description="Permission level")]
    performed_by: Annotated[str, Field(description="Admin who performed the action")]
    message: Annotated[str, Field(description="Human-readable result message")]
    timestamp: Annotated[datetime, Field(description="When the action was performed")]


# ===== ENDPOINTS =====


@router.post(
    "/approve",
    response_model=ApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve an access request",
    description="Approve a pending access request. Adds the user to the tenant group with the requested permission level.",
)
async def approve_request(
    body: ApprovalRequest,
    request: Request,
    authenticated_user: Annotated[KBaseUser, Depends(require_admin)],
):
    """
    Approve a tenant access request.

    This endpoint adds the requester to the specified tenant group.
    Requires CDM_JUPYTERHUB_ADMIN role.
    """
    app_state = get_app_state(request)
    admin_username = authenticated_user.user

    # Get the admin's token from the request to pass through to governance API
    auth_header = request.headers.get("Authorization", "")
    admin_token = auth_header.replace("Bearer ", "") if auth_header else ""

    # Call the governance API to add the user to the group
    read_only = body.permission == "read_only"
    await app_state.governance_client.add_group_member(
        admin_token=admin_token,
        tenant_name=body.tenant_name,
        username=body.requester,
        read_only=read_only,
    )

    # Update the Slack message to show approval
    await app_state.slack_client.update_message_approved(
        channel_id=body.channel_id,
        message_ts=body.message_ts,
        requester=body.requester,
        tenant_name=body.tenant_name,
        permission=body.permission,
        approved_by=admin_username,
    )

    logger.info(
        f"Admin {admin_username} approved access for {body.requester} to tenant {body.tenant_name} ({body.permission})"
    )

    return ApprovalResponse(
        status="approved",
        requester=body.requester,
        tenant_name=body.tenant_name,
        permission=body.permission,
        performed_by=admin_username,
        message=f"Successfully added {body.requester} to {body.tenant_name}",
        timestamp=datetime.now(timezone.utc),
    )


@router.post(
    "/deny",
    response_model=ApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Deny an access request",
    description="Deny a pending access request. No group membership changes are made.",
)
async def deny_request(
    body: ApprovalRequest,
    request: Request,
    authenticated_user: Annotated[KBaseUser, Depends(require_admin)],
):
    """
    Deny a tenant access request.

    This endpoint simply records the denial without making any group changes.
    Requires CDM_JUPYTERHUB_ADMIN role.
    """
    app_state = get_app_state(request)
    admin_username = authenticated_user.user

    # Update the Slack message to show denial
    await app_state.slack_client.update_message_denied(
        channel_id=body.channel_id,
        message_ts=body.message_ts,
        requester=body.requester,
        tenant_name=body.tenant_name,
        denied_by=admin_username,
    )

    logger.info(
        f"Admin {admin_username} denied access for {body.requester} to tenant {body.tenant_name}"
    )

    return ApprovalResponse(
        status="denied",
        requester=body.requester,
        tenant_name=body.tenant_name,
        permission=body.permission,
        performed_by=admin_username,
        message=f"Access request denied for {body.requester}",
        timestamp=datetime.now(timezone.utc),
    )
