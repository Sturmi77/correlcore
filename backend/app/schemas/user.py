"""Pydantic schemas for /user endpoints (Issue #66).

Currently only models the body for ``DELETE /api/v1/user/me`` — the
account deletion request. Kept in its own module (rather than in
``schemas/auth.py``) because user-account self-management is a separate
domain from the auth flow even though the two are adjacent.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DeleteAccountRequest(BaseModel):
    """Body for ``DELETE /api/v1/user/me``.

    Re-authentication via current password is mandatory (defense-in-depth
    against XSRF-via-cookie + stolen-access-token scenarios). The field
    constraints match :class:`app.schemas.auth.RegisterRequest.password`
    so a freshly registered account can be deleted with the password it
    was created with.
    """

    password: str = Field(min_length=8, max_length=128)
