"""
HTTP Bearer authentication for FastAPI.
"""

# Copied from minio_manager_service

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.service import app_state
from src.service.exceptions import MissingTokenError


class KBaseHTTPBearer(HTTPBearer):
    """Custom HTTP Bearer that integrates with KBase auth."""

    def __init__(self):
        super().__init__(auto_error=False)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        """Validate the request and return the authenticated user."""
        user = app_state.get_request_user(request)
        if not user:
            raise MissingTokenError("Authentication required")
        return user
