"""Schemas for the admin console (#677). Admin-only; enforced by require_admin."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminUserListItem(BaseModel):
    """One user row in the admin user list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str | None
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int
    limit: int
    offset: int


class AdminUserDetail(AdminUserListItem):
    updated_at: datetime
    # Default lets us model_validate() straight from the User ORM row (which has
    # no entry_count) and then fill it in via model_copy(update=...).
    entry_count: int = 0


class AdminSetActiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


class AdminMessageResponse(BaseModel):
    message: str
