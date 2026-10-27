#!/usr/bin/env python3
"""Classify whether an autopkgtest control file can use the lightweight unshare backend."""
import argparse
import json
from pathlib import Path

QEMU_ONLY_RESTRICTIONS = {
    "isolation-machine",
    "needs-reboot",
    "needs-reboot-without-mark",
}
UNSHARE_ALLOWED_RESTRICTIONS = {
    "allow-stderr",
    "flaky",
    "hint-testsuite-triggers",
    "isolation-container",
    "needs-internet",
    "needs-root",
    "rw-build-tree",
    "skip-not-installable",
    "superficial",
}


def paragraphs(text):
    current = {}
    last_key = None
    for raw in text.splitlines() + [""]:
        if raw.startswith((" ", "\t")) and last_key:
            current[last_key] += " " + raw.strip()
            continue
        if not raw.strip():
            if current:
                yield current
                current = {}
                last_key = None
            continue
        if ":" not in raw:
            raise SystemExit(f"invalid deb822 test-control line: {raw!r}")
        key, value = raw.split(":", 1)
        last_key = key.strip()
        current[last_key] = value.strip()


def classify(path):
    rows = list(paragraphs(path.read_text()))
    if not rows:
        raise SystemExit("autopkgtest control has no test stanzas")
    tests = []
    qemu_reasons = set()
    unknown_restrictions = set()
    for row in rows:
        names = [name for name in row.get("Tests", "").replace(",", " ").split() if name]
        if not names:
            raise SystemExit("autopkgtest stanza lacks Tests")
        restrictions = {
            item.strip()
            for item in row.get("Restrictions", "").replace(",", " ").split()
            if item.strip()
        }
        qemu_reasons.update(restrictions & QEMU_ONLY_RESTRICTIONS)
        unknown_restrictions.update(
            restriction
            for restriction in restrictions
            if restriction not in QEMU_ONLY_RESTRICTIONS
            and restriction not in UNSHARE_ALLOWED_RESTRICTIONS
        )
        tests.append({
            "tests": names,
            "restrictions": sorted(restrictions),
        })
    backend = "qemu" if qemu_reasons or unknown_restrictions else "unshare"
    return {
        "schema": 1,
        "state": "PASS",
        "backend": backend,
        "qemu_required_restrictions": sorted(qemu_reasons),
        "unknown_restrictions": sorted(unknown_restrictions),
        "stanzas": tests,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control", type=Path)
    args = parser.parse_args()
    if not args.control.is_file():
        parser.error(f"missing autopkgtest control: {args.control}")
    print(json.dumps(classify(args.control), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
