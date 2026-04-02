"""Tests for the GovernanceClient."""

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.governance_client import GovernanceClient
from src.service.exceptions import GovernanceAPIError


class TestGovernanceClientInit:
    """Tests for GovernanceClient initialization."""

    def test_init_with_trailing_slash(self):
        """Test that trailing slash is removed from API URL."""
        client = GovernanceClient(api_url="http://localhost:8000/")
        assert client.api_url == "http://localhost:8000"

    def test_init_without_trailing_slash(self):
        """Test URL without trailing slash remains unchanged."""
        client = GovernanceClient(api_url="http://localhost:8000")
        assert client.api_url == "http://localhost:8000"


class TestAddGroupMember:
    """Tests for add_group_member method."""

    @pytest.mark.asyncio
    async def test_add_group_member_success(self, mock_httpx_client):
        """Test successful group member addition."""
        client = GovernanceClient(api_url="http://localhost:8000")

        with mock_httpx_client(
            status_code=200, json_response={"status": "success", "user": "testuser"}
        ):
            result = await client.add_group_member(
                admin_token="test_admin_token",
                tenant_name="test-tenant",
                username="testuser",
                read_only=False,
            )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_add_group_member_read_only(self, mock_httpx_client):
        """Test adding member to read-only group."""
        client = GovernanceClient(api_url="http://localhost:8000")

        with mock_httpx_client(status_code=200, json_response={"status": "success"}):
            result = await client.add_group_member(
                admin_token="test_admin_token",
                tenant_name="test-tenant",
                username="testuser",
                read_only=True,
            )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_add_group_member_no_token(self):
        """Test that missing admin token raises error."""
        client = GovernanceClient(api_url="http://localhost:8000")

        with pytest.raises(GovernanceAPIError, match="Admin token is required"):
            await client.add_group_member(
                admin_token="",
                tenant_name="test-tenant",
                username="testuser",
                read_only=False,
            )

    @pytest.mark.asyncio
    async def test_add_group_member_api_error(self, mock_httpx_client):
        """Test handling of governance API error."""
        client = GovernanceClient(api_url="http://localhost:8000")

        with mock_httpx_client(status_code=500, raise_error=True):
            with pytest.raises(GovernanceAPIError):
                await client.add_group_member(
                    admin_token="test_admin_token",
                    tenant_name="test-tenant",
                    username="testuser",
                    read_only=False,
                )

    @pytest.mark.asyncio
    async def test_add_group_member_connection_error(self):
        """Test handling of connection errors."""
        client = GovernanceClient(api_url="http://localhost:8000")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.RequestError("Connection failed")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(GovernanceAPIError, match="Failed to connect"):
                await client.add_group_member(
                    admin_token="test_admin_token",
                    tenant_name="test-tenant",
                    username="testuser",
                    read_only=False,
                )


class TestErrorFormatHandling:
    """Tests for different error response formats from governance API."""

    @pytest.mark.asyncio
    async def test_error_with_detail_field(self):
        """Test error response with 'detail' field."""
        client = GovernanceClient(api_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"detail": "User not authorized"}
        mock_response.text = "Forbidden"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(GovernanceAPIError, match="User not authorized"):
                await client.add_group_member(
                    admin_token="token", tenant_name="t", username="u", read_only=False
                )

    @pytest.mark.asyncio
    async def test_error_with_message_field(self):
        """Test error response with 'message' field."""
        client = GovernanceClient(api_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "message": "Bad request data",
            "error_type": "validation",
        }
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(GovernanceAPIError, match="Bad request data"):
                await client.add_group_member(
                    admin_token="token", tenant_name="t", username="u", read_only=False
                )

    @pytest.mark.asyncio
    async def test_error_with_unknown_json_format(self):
        """Test error response with neither detail nor message field."""
        client = GovernanceClient(api_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"code": 500, "info": "Unknown"}
        mock_response.text = "Internal error text"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(GovernanceAPIError, match="Internal error text"):
                await client.add_group_member(
                    admin_token="token", tenant_name="t", username="u", read_only=False
                )

    @pytest.mark.asyncio
    async def test_error_with_non_json_response(self):
        """Test error response where .json() raises."""
        client = GovernanceClient(api_url="http://localhost:8000")

        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "Bad Gateway HTML"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(GovernanceAPIError, match="Bad Gateway HTML"):
                await client.add_group_member(
                    admin_token="token", tenant_name="t", username="u", read_only=False
                )


class TestGroupNameGeneration:
    """Tests for group name generation logic."""

    @pytest.mark.asyncio
    async def test_read_write_group_name(self, mock_httpx_client):
        """Test that read-write uses tenant name directly."""
        client = GovernanceClient(api_url="http://localhost:8000")

        with mock_httpx_client(status_code=200, json_response={"status": "success"}):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "success"}
                mock_response.raise_for_status = MagicMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                await client.add_group_member(
                    admin_token="test_token",
                    tenant_name="my-tenant",
                    username="testuser",
                    read_only=False,
                )

                # Verify the URL contains the tenant name (not suffixed)
                call_args = mock_client.post.call_args
                assert "/my-tenant/members/" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_read_only_group_name(self):
        """Test that read-only adds 'ro' suffix."""
        client = GovernanceClient(api_url="http://localhost:8000")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await client.add_group_member(
                admin_token="test_token",
                tenant_name="my-tenant",
                username="testuser",
                read_only=True,
            )

            # Verify the URL contains the tenant name with 'ro' suffix
            call_args = mock_client.post.call_args
            assert "/my-tenantro/members/" in call_args[0][0]
