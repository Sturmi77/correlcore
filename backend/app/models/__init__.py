"""Model registry — import all models here so Alembic auto-detects them.

Every new model module must be imported in this file.
Alembic's env.py does ``import app.models`` which triggers this file.
"""

from app.models.admin_audit_log import AdminAuditLog  # noqa: F401
from app.models.consent_log import ConsentLog  # noqa: F401
from app.models.device_token import DeviceToken, PushPlatform, PushProvider  # noqa: F401
from app.models.email_verification_token import EmailVerificationToken  # noqa: F401
from app.models.entry import Entry, EntrySlot, NoteVisibility, WorkContext  # noqa: F401
from app.models.entry_note import EntryNoteMarker, EntryNoteSignal, NoteMarkerSource  # noqa: F401
from app.models.insight import Insight, InsightTier, InsightType  # noqa: F401
from app.models.insight_digest import InsightDigest  # noqa: F401
from app.models.insight_dismissal import InsightDismissal  # noqa: F401
from app.models.password_reset_token import PasswordResetToken  # noqa: F401
from app.models.symptom import (  # noqa: F401
    INTENSITY_MAX,
    INTENSITY_MIN,
    STANDARD_SYMPTOM_KEYS,
    EntrySymptom,
    Symptom,
    default_symptom_uuid,
)
from app.models.sync_conflict import SyncConflict  # noqa: F401
from app.models.sync_engine import (  # noqa: F401
    SyncClientState,
    SyncPushBatch,
    SyncRevisionLog,
    SyncUserRevision,
)
from app.models.tag import EntryTag, Tag, TagCategory  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_encryption_key import UserEncryptionKey  # noqa: F401
from app.models.user_preference import UserPreference  # noqa: F401
from app.models.user_profile import UserProfile  # noqa: F401
from app.models.worker_run import (  # noqa: F401
    WorkerJobKind,
    WorkerRun,
    WorkerRunStatus,
    WorkerTriggerSource,
)

__all__ = [
    "INTENSITY_MAX",
    "INTENSITY_MIN",
    "STANDARD_SYMPTOM_KEYS",
    "AdminAuditLog",
    "ConsentLog",
    "DeviceToken",
    "EmailVerificationToken",
    "PushPlatform",
    "PushProvider",
    "Entry",
    "EntryNoteMarker",
    "EntryNoteSignal",
    "EntrySlot",
    "NoteMarkerSource",
    "NoteVisibility",
    "EntrySymptom",
    "EntryTag",
    "Insight",
    "InsightDigest",
    "InsightDismissal",
    "InsightTier",
    "InsightType",
    "PasswordResetToken",
    "Symptom",
    "SyncConflict",
    "SyncClientState",
    "SyncPushBatch",
    "SyncRevisionLog",
    "SyncUserRevision",
    "Tag",
    "TagCategory",
    "User",
    "UserEncryptionKey",
    "UserPreference",
    "WorkContext",
    "WorkerJobKind",
    "WorkerRun",
    "WorkerRunStatus",
    "WorkerTriggerSource",
    "default_symptom_uuid",
]
