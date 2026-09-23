"""Fail a CI integration module when pytest reports skipped test cases."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: assert_junit_no_skips.py <junit.xml>", file=sys.stderr)
        return 2

    report = Path(sys.argv[1])
    root = ET.parse(report).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    skipped = sum(int(suite.attrib.get("skipped", "0")) for suite in suites)
    tests = sum(int(suite.attrib.get("tests", "0")) for suite in suites)

    if tests == 0:
        print(f"{report}: no integration tests executed", file=sys.stderr)
        return 1
    if skipped:
        print(f"{report}: {skipped} of {tests} integration tests skipped", file=sys.stderr)
        return 1

    print(f"{report}: all {tests} integration tests executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
