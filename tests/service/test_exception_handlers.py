"""Tests for exception handlers."""

import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError

from src.service.exception_handlers import universal_error_handler, _format_error
from src.service.exceptions import (
    TenantAccessError,
    SlackSignatureError,
    SlackError,
    GovernanceAPIError,
)


class TestFormatError:
    """Tests for the _format_error helper function."""

    def test_format_error_with_all_params(self):
        """Test formatting error with all parameters."""
        response = _format_error(
            status_code=400,
            error_code=1001,
            error_type_str="validation_error",
            message="Invalid input",
        )
        assert response.status_code == 400
        data = response.body.decode()
        assert "validation_error" in data
        assert "Invalid input" in data

    def test_format_error_with_none_message(self):
        """Test formatting error when message is None."""
        response = _format_error(
            status_code=500,
            error_code=None,
            error_type_str="internal_error",
            message=None,
        )
        assert response.status_code == 500
        data = response.body.decode()
        assert "internal_error" in data

    def test_format_error_with_no_type_or_message(self):
        """Test formatting error with no type or message defaults to Unknown error."""
        response = _format_error(
            status_code=500,
            error_code=None,
            error_type_str=None,
            message=None,
        )
        assert response.status_code == 500
        data = response.body.decode()
        assert "Unknown error" in data


class TestUniversalErrorHandler:
    """Tests for the universal_error_handler function."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/test"
        return request

    @pytest.mark.asyncio
    async def test_slack_signature_error(self, mock_request):
        """Test handling SlackSignatureError."""
        exc = SlackSignatureError("Invalid signature")
        response = await universal_error_handler(mock_request, exc)

        assert response.status_code == 401
        data = response.body.decode()
        assert "slack_signature_invalid" in data
        assert "Invalid signature" in data

    @pytest.mark.asyncio
    async def test_tenant_access_error(self, mock_request):
        """Test handling TenantAccessError."""
        exc = TenantAccessError("Access denied to tenant")
        response = await universal_error_handler(mock_request, exc)

        assert response.status_code == 400
        data = response.body.decode()
        assert "TenantAccessError" in data
        assert "Access denied to tenant" in data

    @pytest.mark.asyncio
    async def test_slack_error_subclass(self, mock_request):
        """Test handling SlackError (subclass of TenantAccessError)."""
        exc = SlackError("Failed to send message")
        response = await universal_error_handler(mock_request, exc)

        assert response.status_code == 400
        data = response.body.decode()
        assert "SlackError" in data
        assert "Failed to send message" in data

    @pytest.mark.asyncio
    async def test_governance_api_error_subclass(self, mock_request):
        """Test handling GovernanceAPIError (subclass of TenantAccessError)."""
        exc = GovernanceAPIError("API connection failed")
        response = await universal_error_handler(mock_request, exc)

        assert response.status_code == 400
        data = response.body.decode()
        assert "GovernanceAPIError" in data
        assert "API connection failed" in data

    @pytest.mark.asyncio
    async def test_http_exception(self, mock_request):
        """Test handling HTTPException."""
        exc = HTTPException(status_code=404, detail="Not found")
        response = await universal_error_handler(mock_request, exc)

        assert response.status_code == 404
        data = response.body.decode()
        assert "Not found" in data

    @pytest.mark.asyncio
    async def test_http_exception_403(self, mock_request):
        """Test handling 403 Forbidden HTTPException."""
        exc = HTTPException(status_code=403, detail="Forbidden")
        response = await universal_error_handler(mock_request, exc)

        assert response.status_code == 403
        data = response.body.decode()
        assert "Forbidden" in data

    @pytest.mark.asyncio
    async def test_request_validation_error(self, mock_request):
        """Test handling RequestValidationError."""
        # Create a mock validation error
        exc = RequestValidationError(
            errors=[
                {
                    "loc": ["body", "field"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ]
        )
        response = await universal_error_handler(mock_request, exc)

        assert response.status_code == 400
        data = response.body.decode()
        assert "request_validation_failed" in data

    @pytest.mark.asyncio
    async def test_generic_exception(self, mock_request):
        """Test handling generic/unexpected exceptions."""
        exc = RuntimeError("Something went wrong")
        response = await universal_error_handler(mock_request, exc)

        assert response.status_code == 500
        data = response.body.decode()
        assert "An unexpected error occurred" in data

    @pytest.mark.asyncio
    async def test_tenant_access_error_empty_message(self, mock_request):
        """Test handling TenantAccessError with empty message."""
        exc = TenantAccessError("")
        response = await universal_error_handler(mock_request, exc)

        assert response.status_code == 400
        data = response.body.decode()
        assert "TenantAccessError" in data
