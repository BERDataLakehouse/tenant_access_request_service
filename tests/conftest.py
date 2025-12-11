"""
Shared test fixtures for the tenant_access_request_service test suite.

Provides reusable mocks for external dependencies:
- Slack: Mock slack_sdk WebClient and signature verification
- Governance API: Mock httpx client for governance API calls
- KBase Auth: Mock authentication and authorization
- FastAPI: Mock app with dependency overrides
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from src.core.governance_client import GovernanceClient
from src.core.slack_client import SlackClient
from src.main import create_application
from src.service.app_state import AppState
from src.service.dependencies import auth, require_admin
from src.service.kb_auth import AdminPermission, KBaseUser


# =============================================================================
# KBase Auth Fixtures
# =============================================================================


@pytest.fixture
def mock_kbase_user():
    """Factory for creating mock KBaseUser instances."""

    def _create_user(
        username: str = "testuser", admin_perm: AdminPermission = AdminPermission.NONE
    ) -> KBaseUser:
        return KBaseUser(user=username, admin_perm=admin_perm)

    return _create_user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin KBaseUser."""
    return KBaseUser(user="adminuser", admin_perm=AdminPermission.FULL)


@pytest.fixture
def mock_regular_user():
    """Create a mock regular KBaseUser."""
    return KBaseUser(user="regularuser", admin_perm=AdminPermission.NONE)


# =============================================================================
# Slack Client Fixtures
# =============================================================================


@pytest.fixture
def mock_slack_web_client():
    """
    Create a mock Slack WebClient.

    Supports:
    - chat_postMessage: Mock sending messages
    - chat_update: Mock updating messages
    """
    client = MagicMock()

    # Mock successful message posting
    client.chat_postMessage = MagicMock(
        return_value={"ok": True, "ts": "1234567890.123456", "channel": "C12345"}
    )

    # Mock successful message update
    client.chat_update = MagicMock(return_value={"ok": True})

    return client


@pytest.fixture
def mock_slack_client(mock_slack_web_client):
    """
    Create a mock SlackClient with mocked WebClient.
    """
    with patch.object(SlackClient, "__init__", lambda self, *args, **kwargs: None):
        slack_client = SlackClient.__new__(SlackClient)
        slack_client.client = mock_slack_web_client
        slack_client.signing_secret = "test_signing_secret"
        slack_client.channel_id = "C12345"
        yield slack_client


# =============================================================================
# Governance Client Fixtures
# =============================================================================


@pytest.fixture
def mock_governance_client():
    """
    Create a mock GovernanceClient.
    """
    client = MagicMock(spec=GovernanceClient)
    client.api_url = "http://test-governance-api:8000"
    client.add_group_member = AsyncMock(
        return_value={"status": "success", "message": "User added to group"}
    )
    return client


@pytest.fixture
def mock_httpx_client():
    """
    Mock httpx.AsyncClient for governance API calls.

    Usage:
        with mock_httpx_client(status_code=200, json_response={"status": "success"}):
            result = await governance_client.add_group_member(...)
    """

    def _configure_client(
        status_code: int = 200, json_response: dict = None, raise_error: bool = False
    ):
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json = MagicMock(
            return_value=json_response or {"status": "success"}
        )
        mock_response.text = "OK"
        mock_response.raise_for_status = MagicMock()

        if raise_error:
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=mock_response
            )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.get = AsyncMock(return_value=mock_response)

        @asynccontextmanager
        async def mock_context(*args, **kwargs):
            yield mock_client

        return patch("httpx.AsyncClient", mock_context)

    return _configure_client


# =============================================================================
# Request Data Fixtures
# =============================================================================


@pytest.fixture
def sample_access_request():
    """Factory for creating sample access request data."""

    def _create_request(
        tenant_name: str = "test-tenant",
        permission: str = "read_only",
        justification: str = "Need access for testing",
    ) -> dict:
        return {
            "tenant_name": tenant_name,
            "permission": permission,
            "justification": justification,
        }

    return _create_request


@pytest.fixture
def sample_approval_request():
    """Factory for creating sample approval request data."""

    def _create_approval(
        requester: str = "testuser",
        tenant_name: str = "test-tenant",
        permission: str = "read_only",
        channel_id: str = "C12345",
        message_ts: str = "1234567890.123456",
    ) -> dict:
        return {
            "requester": requester,
            "tenant_name": tenant_name,
            "permission": permission,
            "channel_id": channel_id,
            "message_ts": message_ts,
        }

    return _create_approval


@pytest.fixture
def sample_slack_interaction_payload():
    """Factory for creating sample Slack interaction payloads."""

    def _create_payload(
        action_id: str = "approve_tenant_access",
        user_id: str = "U12345",
        user_name: str = "adminuser",
        channel_id: str = "C12345",
        message_ts: str = "1234567890.123456",
        value: str = "eyJ1IjogInRlc3R1c2VyIiwgInQiOiAidGVzdC10ZW5hbnQiLCAicCI6ICJybyIsICJ0cyI6IDE3MDAwMDAwMDB9",
    ) -> dict:
        return {
            "type": "block_actions",
            "user": {"id": user_id, "username": user_name},
            "channel": {"id": channel_id},
            "message": {"ts": message_ts},
            "actions": [{"action_id": action_id, "value": value}],
        }

    return _create_payload


# =============================================================================
# FastAPI Testing Fixtures
# =============================================================================


@pytest.fixture
def mock_app_state(mock_slack_client, mock_governance_client):
    """Create mock application state."""

    mock_auth = MagicMock()
    mock_auth.get_user = AsyncMock(
        return_value=KBaseUser(user="testuser", admin_perm=AdminPermission.NONE)
    )

    return AppState(
        auth=mock_auth,
        slack_client=mock_slack_client,
        governance_client=mock_governance_client,
    )


@pytest.fixture
def client():
    """
    Basic test client without mocked dependencies.

    Note: This requires actual services to be available.
    Use mock_app fixture for unit tests with mocks.
    """
    app = create_application()
    return TestClient(app)


@pytest.fixture
def mock_app(mock_kbase_user, mock_admin_user, mock_app_state):
    """
    Create a FastAPI app with mocked dependencies for route testing.

    Returns tuple: (app, mock_app_state)
    """
    app = create_application()

    # Create mock user
    user = mock_kbase_user()

    # Mock auth dependency
    def mock_auth_dep():
        return user

    # Mock admin dependency
    def mock_admin_dep():
        return mock_admin_user

    app.dependency_overrides[auth] = mock_auth_dep
    app.dependency_overrides[require_admin] = mock_admin_dep

    # Mock app state
    app.state._app_state = mock_app_state
    app.state._auth = mock_app_state.auth

    return app, mock_app_state


@pytest.fixture
def test_client(mock_app):
    """
    Create a TestClient with mocked dependencies.

    Usage:
        def test_endpoint(test_client):
            response = test_client.get("/health")
            assert response.status_code == 200
    """
    app, _ = mock_app
    return TestClient(app)


@pytest.fixture
def admin_test_client(mock_app, mock_admin_user):
    """
    Create a TestClient with admin user for admin-only endpoints.
    """
    app, _ = mock_app

    def mock_admin_auth():
        return mock_admin_user

    app.dependency_overrides[auth] = mock_admin_auth
    app.dependency_overrides[require_admin] = mock_admin_auth

    return TestClient(app)
