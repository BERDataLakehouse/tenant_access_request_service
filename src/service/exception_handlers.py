"""
Exception handlers for the FastAPI application.
"""

import logging

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.service.exceptions import TenantAccessError, SlackSignatureError
from src.service.models import ErrorResponse

logger = logging.getLogger(__name__)


def _format_error(
    status_code: int,
    error_code: int | None,
    error_type_str: str | None,
    message: str | None,
):
    """Format error response with consistent structure."""
    error_response = ErrorResponse(
        error=error_code,
        error_type=error_type_str,
        message=message or error_type_str or "Unknown error",
    )
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(),
    )


async def universal_error_handler(request: Request, exc: Exception):
    """
    Universal handler for all types of exceptions.
    """
    # Default values
    error_code = None
    error_type_str = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, SlackSignatureError):
        status_code = status.HTTP_401_UNAUTHORIZED
        error_type_str = "slack_signature_invalid"
        message = str(exc)

    elif isinstance(exc, TenantAccessError):
        # Handle TenantAccessError and subclasses
        status_code = status.HTTP_400_BAD_REQUEST
        error_type_str = type(exc).__name__
        message = str(exc) if str(exc) else error_type_str

    elif isinstance(exc, RequestValidationError):
        # Handle validation errors from request parsing
        status_code = status.HTTP_400_BAD_REQUEST
        error_type_str = "request_validation_failed"
        message = str(exc.errors())

    elif isinstance(exc, HTTPException):
        # Handle FastAPI Exceptions
        status_code = exc.status_code
        message = str(exc.detail)

    else:
        # Handle all other generic exceptions
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        message = "An unexpected error occurred"

    return _format_error(status_code, error_code, error_type_str, message)
