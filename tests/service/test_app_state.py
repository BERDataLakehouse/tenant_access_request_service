"""Tests for the app state module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.service.app_state import (
    AppState,
    RequestState,
    _get_app_state_from_app,
    build_app,
    destroy_app_state,
    get_app_state,
    get_request_user,
    set_request_user,
)
from src.service.kb_auth import AdminPermission, KBaseUser


class TestBuildApp:
    """Tests for build_app function."""

    @pytest.mark.asyncio
    async def test_build_app_initializes_state(self):
        mock_app = MagicMock()
        mock_app.state = MagicMock()

        with (
            patch(
                "src.service.app_state.KBaseAuth.create",
                new_callable=AsyncMock,
            ) as mock_create,
            patch.dict(
                "os.environ",
                {
                    "SLACK_BOT_TOKEN": "xoxb-test",
                    "SLACK_SIGNING_SECRET": "test-secret",
                    "SLACK_CHANNEL_ID": "C12345",
                    "GOVERNANCE_API_URL": "http://gov:8000",
                },
            ),
            patch("src.service.app_state.SlackClient") as mock_slack_cls,
            patch("src.service.app_state.GovernanceClient") as mock_gov_cls,
        ):
            mock_auth = MagicMock()
            mock_create.return_value = mock_auth
            mock_slack = MagicMock()
            mock_slack_cls.return_value = mock_slack
            mock_gov = MagicMock()
            mock_gov_cls.return_value = mock_gov

            await build_app(mock_app)

        assert isinstance(mock_app.state._app_state, AppState)
        assert mock_app.state._auth == mock_auth

    @pytest.mark.asyncio
    async def test_build_app_uses_env_vars(self):
        mock_app = MagicMock()
        mock_app.state = MagicMock()

        with (
            patch.dict(
                "os.environ",
                {
                    "KBASE_AUTH_URL": "http://custom/auth/",
                    "KBASE_ADMIN_ROLES": "ADMIN1,ADMIN2",
                    "KBASE_REQUIRED_ROLES": "ROLE1,ROLE2",
                    "SLACK_BOT_TOKEN": "xoxb-test",
                    "SLACK_SIGNING_SECRET": "test-secret",
                    "SLACK_CHANNEL_ID": "C12345",
                    "GOVERNANCE_API_URL": "http://gov:8000",
                },
            ),
            patch(
                "src.service.app_state.KBaseAuth.create",
                new_callable=AsyncMock,
            ) as mock_create,
            patch("src.service.app_state.SlackClient"),
            patch("src.service.app_state.GovernanceClient"),
        ):
            mock_create.return_value = MagicMock()
            await build_app(mock_app)

        mock_create.assert_called_once_with(
            "http://custom/auth/",
            required_roles=["ROLE1", "ROLE2"],
            full_admin_roles=["ADMIN1", "ADMIN2"],
        )

    @pytest.mark.asyncio
    async def test_build_app_missing_slack_token_raises(self):
        mock_app = MagicMock()
        mock_app.state = MagicMock()

        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "src.service.app_state.KBaseAuth.create",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
        ):
            with pytest.raises(ValueError, match="SLACK_BOT_TOKEN"):
                await build_app(mock_app)


class TestDestroyAppState:
    """Tests for destroy_app_state function."""

    @pytest.mark.asyncio
    async def test_destroy_app_state_completes(self):
        mock_app = MagicMock()
        await destroy_app_state(mock_app)


class TestGetAppState:
    """Tests for get_app_state and _get_app_state_from_app."""

    def test_get_app_state_success(self):
        mock_request = MagicMock()
        mock_auth = MagicMock()
        mock_slack = MagicMock()
        mock_gov = MagicMock()
        expected_state = AppState(auth=mock_auth, slack_client=mock_slack, governance_client=mock_gov)
        mock_request.app.state._app_state = expected_state
        result = get_app_state(mock_request)
        assert result == expected_state

    def test_get_app_state_not_initialized(self):
        mock_app = MagicMock(spec=[])
        mock_app.state = MagicMock(spec=[])
        with pytest.raises(ValueError, match="App state has not been initialized"):
            _get_app_state_from_app(mock_app)

    def test_get_app_state_none_value(self):
        mock_app = MagicMock()
        mock_app.state._app_state = None
        with pytest.raises(ValueError, match="App state has not been initialized"):
            _get_app_state_from_app(mock_app)


class TestRequestUser:
    """Tests for set_request_user and get_request_user."""

    def test_set_and_get_request_user(self):
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        user = KBaseUser("testuser", AdminPermission.NONE)
        set_request_user(mock_request, user)
        assert mock_request.state._request_state == RequestState(user=user)

    def test_set_request_user_none(self):
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        set_request_user(mock_request, None)
        assert mock_request.state._request_state == RequestState(user=None)

    def test_get_request_user_not_set(self):
        mock_request = MagicMock(spec=[])
        mock_request.state = MagicMock(spec=[])
        result = get_request_user(mock_request)
        assert result is None

    def test_get_request_user_none_state(self):
        mock_request = MagicMock()
        mock_request.state._request_state = None
        result = get_request_user(mock_request)
        assert result is None
