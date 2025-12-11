"""
Governance API client for interacting with minio_manager_service.
"""

import logging

import httpx

from src.service.exceptions import GovernanceAPIError

logger = logging.getLogger(__name__)


class GovernanceClient:
    """Client for interacting with the minio_manager_service governance API."""

    def __init__(self, api_url: str):
        """
        Initialize the Governance client.

        Args:
            api_url: URL of the minio_manager_service governance API
        """
        self.api_url = api_url.rstrip("/")

    async def add_group_member(
        self,
        admin_token: str,
        tenant_name: str,
        username: str,
        read_only: bool,
    ) -> dict:
        """
        Call the governance API to add a user to a group.

        Args:
            admin_token: KBase auth token of the admin performing the action
            tenant_name: Name of the tenant/group
            username: Username to add
            read_only: If True, adds to read-only group

        Returns:
            Response from the governance API
        """
        if not admin_token:
            raise GovernanceAPIError("Admin token is required to call governance API.")

        group_name = f"{tenant_name}ro" if read_only else tenant_name
        url = f"{self.api_url}/management/groups/{group_name}/members/{username}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=30.0,
                )
                response.raise_for_status()
                logger.info(f"Added {username} to group {group_name}")
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_json = e.response.json()
                    # Handle different error formats
                    # {"detail": "..."} or {"message": "...", "error_type": "..."}
                    if "detail" in error_json:
                        error_detail = error_json["detail"]
                    elif "message" in error_json:
                        error_detail = error_json["message"]
                    else:
                        error_detail = e.response.text
                except Exception:
                    error_detail = e.response.text
                logger.error(
                    f"Governance API error: {e.response.status_code} - {error_detail}"
                )
                raise GovernanceAPIError(f"{error_detail}")
            except httpx.RequestError as e:
                logger.error(f"Governance API request failed: {e}")
                raise GovernanceAPIError(f"Failed to connect to governance API: {e}")
