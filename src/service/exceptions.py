"""
Custom exceptions for the Tenant Access Request Service.
"""


class TenantAccessError(Exception):
    """
    The super class of all Tenant Access Service related errors.
    """


class AuthenticationError(TenantAccessError):
    """
    Super class for authentication related errors.
    """


class MissingTokenError(AuthenticationError):
    """
    An error thrown when a token is required but absent.
    """


class InvalidAuthHeaderError(AuthenticationError):
    """
    An error thrown when an authorization header is invalid.
    """


class InvalidTokenError(AuthenticationError):
    """
    An error thrown when a user's token is invalid.
    """


class MissingRoleError(AuthenticationError):
    """
    An error thrown when a user is missing a required role.
    """


# ----- Service specific exceptions -----


class SlackError(TenantAccessError):
    """Raised when Slack API operations fail."""

    pass


class SlackSignatureError(TenantAccessError):
    """Raised when Slack request signature verification fails."""

    pass


class GovernanceAPIError(TenantAccessError):
    """Raised when Governance API operations fail."""

    pass


class RequestValidationError(TenantAccessError):
    """Raised when request validation fails."""

    pass
