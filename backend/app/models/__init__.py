"""Model registry — import all models here so Alembic auto-detects them.

Every new model module must be imported in this file.
Alembic's env.py does ``import app.models`` which triggers this file.
"""

from app.models.email_verification_token import EmailVerificationToken  # noqa: F401
from app.models.entry import Entry, EntrySlot, WorkContext  # noqa: F401
from app.models.symptom import (  # noqa: F401
    INTENSITY_MAX,
    INTENSITY_MIN,
    STANDARD_SYMPTOM_KEYS,
    EntrySymptom,
)
from app.models.tag import EntryTag, Tag, TagCategory  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "INTENSITY_MAX",
    "INTENSITY_MIN",
    "STANDARD_SYMPTOM_KEYS",
    "EmailVerificationToken",
    "Entry",
    "EntrySlot",
    "EntrySymptom",
    "EntryTag",
    "Tag",
    "TagCategory",
    "User",
    "WorkContext",
]
