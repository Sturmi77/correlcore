"""Model registry — import all models here so Alembic auto-detects them.

Every new model module must be imported in this file.
Alembic's env.py does ``import app.models`` which triggers this file.
"""

from app.models.user import User  # noqa: F401

__all__ = ["User"]
