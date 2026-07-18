"""Neutral push notification copy (DESIGN_DOCUMENT §2.15 / DSGVO).

Never include mood scores, notes, tags, or other Art. 9 content in payloads.
"""

from __future__ import annotations

# English product copy — keep stable for FCM / store review consistency.
CHECK_IN_REMINDER_TITLE = "CorrelCore"
CHECK_IN_REMINDER_BODY = "Time for your daily check-in."
