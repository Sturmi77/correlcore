"""Reject a packaged scan whose HTTP coverage was masked by rate limiting.

Hook API: https://www.zaproxy.org/docs/docker/scan-hooks/
Only status counts are persisted; requests may contain credentials.
"""

import json
from pathlib import Path


def zap_pre_shutdown(zap):
    statuses = {}
    start = 0
    while True:
        messages = zap.core.messages(start=start, count=500)
        if not isinstance(messages, list):
            raise RuntimeError("ZAP HTTP history unavailable; coverage is unverified")
        for message in messages:
            header = message.get("responseHeader", "").splitlines()
            parts = header[0].split() if header else []
            status = parts[1] if len(parts) > 1 else "missing"
            statuses[status] = statuses.get(status, 0) + 1
        start += len(messages)
        if len(messages) < 500:
            break
    Path("/zap/wrk/http-coverage.json").write_text(
        json.dumps(statuses), encoding="utf-8"
    )
