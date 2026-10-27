#!/usr/bin/env python3
"""Report likely live-network dependencies in upstream test source code."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CODE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".py", ".qml", ".sh"}
TEST_PARTS = {"test", "tests", "autotest", "autotests"}
URL_RE = re.compile(r"https?://[^\\s\"'<>]+", re.IGNORECASE)
DOMAIN_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"([A-Za-z0-9](?:[A-Za-z0-9.-]{1,120})\\.(?:org|com|net|io|dev|test))"
    r"(?![A-Za-z0-9_.-])",
    re.IGNORECASE,
)
IGNORED = {
    "example.com", "example.org", "example.net",
    "localhost.localdomain",
}


def testish(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return bool(parts & TEST_PARTS) or any("test" in part.lower() for part in path.parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.source.resolve()
    if not root.is_dir():
        raise SystemExit(f"missing source tree: {root}")

    findings = []
    scanned = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in CODE_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if not testish(relative):
            continue
        scanned += 1
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        values = set(URL_RE.findall(text))
        values.update(DOMAIN_RE.findall(text))
        for value in sorted(values):
            lower = value.lower().rstrip("/.,);]")
            if lower in IGNORED:
                continue
            if "127.0.0.1" in lower or "localhost" in lower:
                continue
            findings.append({"file": str(relative), "endpoint": value})

    result = {
        "schema": 1,
        "state": "PASS",
        "kind": "upstream-test-live-network-static-review",
        "scanned_test_source_files": scanned,
        "candidate_count": len(findings),
        "candidates": findings,
        "blocking": False,
        "interpretation": (
            "Candidates require review before authoritative execution; "
            "static detection alone is not a package failure."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        f"Upstream test network scan: PASS; scanned={scanned} candidates={len(findings)}"
    )


if __name__ == "__main__":
    main()
