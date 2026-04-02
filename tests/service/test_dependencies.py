"""Tests for the dependencies module."""

import pytest
from fastapi import HTTPException

from src.service.dependencies import require_admin, require_authenticated
from src.service.kb_auth import AdminPermission, KBaseUser


class TestRequireAuthenticated:
    """Tests for the require_authenticated dependency."""

    def test_returns_user(self):
        user = KBaseUser("testuser", AdminPermission.NONE)
        result = require_authenticated(user)
        assert result == user


class TestRequireAdmin:
    """Tests for the require_admin dependency."""

    def test_admin_user_passes(self):
        admin = KBaseUser("admin", AdminPermission.FULL)
        result = require_admin(admin)
        assert result == admin

    def test_non_admin_raises_403(self):
        user = KBaseUser("regular", AdminPermission.NONE)
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)
        assert exc_info.value.status_code == 403
        assert "Administrator privileges" in exc_info.value.detail
