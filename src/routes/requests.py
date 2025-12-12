"""
Access Request Routes for the Tenant Access Request Service.

This module provides endpoints for users to submit tenant access requests.
These are user-facing endpoints that any authenticated BERDL user can call.
"""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from src.service.app_state import get_app_state
from src.service.dependencies import auth
from src.service.kb_auth import KBaseUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requests", tags=["requests"])


# ===== RESPONSE MODELS =====


class AccessRequestCreate(BaseModel):
    """Request body for creating an access request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    tenant_name: Annotated[
        str, Field(description="Name of the tenant to request access to", min_length=1)
    ]
    permission: Annotated[
        Literal["read_only", "read_write"],
        Field(description="Permission level: read_only or read_write"),
    ] = "read_only"
    justification: Annotated[
        str | None, Field(description="Optional justification for the request")
    ] = None


class AccessRequestResponse(BaseModel):
    """Response for created access request."""

    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    status: Annotated[str, Field(description="Status of the request")]
    message: Annotated[str, Field(description="Human-readable message")]
    requester: Annotated[str, Field(description="Username of the requester")]
    tenant_name: Annotated[str, Field(description="Requested tenant name")]
    permission: Annotated[str, Field(description="Requested permission level")]


# ===== ENDPOINTS =====


@router.post(
    "/",
    response_model=AccessRequestResponse,
    summary="Submit a tenant access request",
    description="Submit a request to join a tenant group. Sends a notification to the admin Slack channel for approval.",
)
async def create_access_request(
    body: AccessRequestCreate,
    authenticated_user: Annotated[KBaseUser, Depends(auth)],
    request: Request,
):
    """
    Submit an access request for a tenant group.

    The request will be sent to a Slack channel configured by the SLACK_CHANNEL_ID
    environment variable where admins can review and approve/deny.
    """
    app_state = get_app_state(request)
    username = authenticated_user.user

    # Send the request to Slack
    await app_state.slack_client.send_access_request(
        requester=username,
        tenant_name=body.tenant_name,
        permission=body.permission,
        justification=body.justification,
    )

    logger.info(
        f"User {username} submitted access request for tenant {body.tenant_name} ({body.permission})"
    )

    return AccessRequestResponse(
        status="submitted",
        message="Request received by KBase admin for approval. Call get_my_groups() to check your membership after approval.",
        requester=username,
        tenant_name=body.tenant_name,
        permission=body.permission,
    )
