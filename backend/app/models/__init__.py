"""Model registry — import all models here so Alembic auto-detects them.

Every new model module must be imported in this file.
Alembic's env.py does ``import app.models`` which triggers this file.
"""

from app.models.email_verification_token import EmailVerificationToken  # noqa: F401
from app.models.entry import Entry, EntrySlot, WorkContext  # noqa: F401
from app.models.insight import Insight, InsightTier, InsightType  # noqa: F401
from app.models.symptom import (  # noqa: F401
    INTENSITY_MAX,
    INTENSITY_MIN,
    STANDARD_SYMPTOM_KEYS,
    EntrySymptom,
    Symptom,
    default_symptom_uuid,
)
from app.models.sync_conflict import SyncConflict  # noqa: F401
from app.models.tag import EntryTag, Tag, TagCategory  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_encryption_key import UserEncryptionKey  # noqa: F401
from app.models.user_preference import UserPreference  # noqa: F401
from app.models.user_profile import UserProfile  # noqa: F401

__all__ = [
    "INTENSITY_MAX",
    "INTENSITY_MIN",
    "STANDARD_SYMPTOM_KEYS",
    "EmailVerificationToken",
    "Entry",
    "EntrySlot",
    "EntrySymptom",
    "EntryTag",
    "Insight",
    "InsightTier",
    "InsightType",
    "Symptom",
    "SyncConflict",
    "Tag",
    "TagCategory",
    "User",
    "UserEncryptionKey",
    "UserPreference",
    "WorkContext",
    "default_symptom_uuid",
]
