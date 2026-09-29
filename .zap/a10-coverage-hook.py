"""Reject a packaged scan whose HTTP coverage was masked by rate limiting.

Hook API: https://www.zaproxy.org/docs/docker/scan-hooks/
Only status counts are persisted; requests may contain credentials.
"""

import json
from pathlib import Path
from urllib.parse import urlsplit


REQUIRED_PROTECTED_ROUTES = ("/api/v1/entries", "/api/v1/insights/latest")


def summarize_messages(messages, statuses, protected):
    for message in messages:
        header = message.get("responseHeader", "").splitlines()
        parts = header[0].split() if header else []
        status = parts[1] if len(parts) > 1 else "missing"
        statuses[status] = statuses.get(status, 0) + 1
        request = message.get("requestHeader", "").splitlines()
        request_parts = request[0].split() if request else []
        if len(request_parts) < 2 or request_parts[0] != "GET":
            continue
        path = urlsplit(request_parts[1]).path.rstrip("/")
        if path in protected and status.isdigit() and 200 <= int(status) < 300:
            protected[path] += 1


def coverage_passed(evidence):
    return (
        bool(evidence["statuses"])
        and "429" not in evidence["statuses"]
        and all(
            evidence["protected"].get(path, 0) > 0 for path in REQUIRED_PROTECTED_ROUTES
        )
    )


def zap_pre_shutdown(zap):
    statuses = {}
    protected = dict.fromkeys(REQUIRED_PROTECTED_ROUTES, 0)
    start = 0
    while True:
        messages = zap.core.messages(start=start, count=500)
        if not isinstance(messages, list):
            raise RuntimeError("ZAP HTTP history unavailable; coverage is unverified")
        summarize_messages(messages, statuses, protected)
        start += len(messages)
        if len(messages) < 500:
            break
    evidence = {"statuses": statuses, "protected": protected}
    evidence["passed"] = coverage_passed(evidence)
    Path("/zap/wrk/http-coverage.json").write_text(
        json.dumps(evidence), encoding="utf-8"
    )
