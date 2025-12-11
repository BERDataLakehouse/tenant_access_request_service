"""
Argument validation helper functions.
"""

# Copied from minio_manager_service


def not_falsy(val, name: str):
    """
    Check that a value is not falsy.

    Args:
        val: The value to check.
        name: The name of the value for error messages.

    Returns:
        The value if it is not falsy.

    Raises:
        ValueError: If the value is falsy.
    """
    if not val:
        raise ValueError(f"{name} is required and cannot be empty")
    return val
