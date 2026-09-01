#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

HEADER_RE = re.compile(r"^### (\S+) (\S+) origin=(\S+)$")
FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*:")
SHA512_ROW_RE = re.compile(r"^([0-9a-fA-F]{128})\s+(\d+)\s+(\S+)$")
UBUNTU_ORIGIN_RE = re.compile(r"^ubuntu-stonking(?:@\d{8}T\d{6}Z|-snapshot)$")

EXPECTED_SECTIONS = 101
EXPECTED_UBUNTU_SECTIONS = 100
EXPECTED_DEBIAN_SECTIONS = 1


def fail(message: str) -> None:
    raise SystemExit(f"AURORA_KSQ_SELECTED_SOURCE_RECORDS_FAILURE: {message}")


def normalize(input_path: Path, output_path: Path) -> None:
    lines = input_path.read_text(encoding="utf-8").splitlines()
    result: list[str] = []
    section_count = 0
    ubuntu_count = 0
    debian_count = 0
    i = 0

    while i < len(lines):
        header = lines[i]
        if not header.startswith("### "):
            fail(f"expected section header at line {i + 1}: {header!r}")
        match = HEADER_RE.fullmatch(header)
        if not match:
            fail(f"invalid section header: {header!r}")

        source, version, origin = match.groups()
        section_count += 1
        result.append(header)
        i += 1

        block: list[str] = []
        while i < len(lines) and not lines[i].startswith("### "):
            block.append(lines[i])
            i += 1

        if origin == "debian-source":
            debian_count += 1
            result.extend(block)
            continue

        if not UBUNTU_ORIGIN_RE.fullmatch(origin):
            fail(f"unexpected source origin for {source}={version}: {origin}")
        ubuntu_count += 1

        checksum_fields = [n for n, line in enumerate(block) if line.rstrip() == "Checksums-Sha512:"]
        if len(checksum_fields) != 1:
            fail(f"{source}={version}: expected exactly one Checksums-Sha512 field, found {len(checksum_fields)}")

        start = checksum_fields[0]
        end = start + 1
        rows: list[tuple[str, int, str]] = []
        while end < len(block):
            line = block[end]
            if FIELD_RE.match(line):
                break
            if line.strip():
                row = SHA512_ROW_RE.fullmatch(line.strip())
                if not row:
                    fail(f"{source}={version}: invalid SHA512 continuation line: {line!r}")
                digest, size, filename = row.groups()
                rows.append((filename, int(size), digest.lower()))
            end += 1

        if not rows:
            fail(f"{source}={version}: empty Checksums-Sha512 block")
        if len({filename for filename, _, _ in rows}) != len(rows):
            fail(f"{source}={version}: duplicate source-object filename in Checksums-Sha512")

        # The certified KSQ-0 artifact deliberately stored selected source records
        # as a flat text serialization: checksum continuation rows have no Deb822
        # indentation. Re-indent only those already-certified rows so the existing
        # Deb822 parser can consume them. No filename, size, hash, source version,
        # origin, field order, or other data is changed.
        result.extend(block[: start + 1])
        for filename, size, digest in rows:
            result.append(f" {digest} {size} {filename}")
        result.extend(block[end:])

    if section_count != EXPECTED_SECTIONS:
        fail(f"source section count mismatch: expected={EXPECTED_SECTIONS} got={section_count}")
    if ubuntu_count != EXPECTED_UBUNTU_SECTIONS:
        fail(f"Ubuntu source section count mismatch: expected={EXPECTED_UBUNTU_SECTIONS} got={ubuntu_count}")
    if debian_count != EXPECTED_DEBIAN_SECTIONS:
        fail(f"Debian source section count mismatch: expected={EXPECTED_DEBIAN_SECTIONS} got={debian_count}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(result) + "\n", encoding="utf-8")

    print(f"AURORA_KSQ_SELECTED_SOURCE_RECORDS_TOTAL={section_count}")
    print(f"AURORA_KSQ_SELECTED_SOURCE_RECORDS_UBUNTU={ubuntu_count}")
    print(f"AURORA_KSQ_SELECTED_SOURCE_RECORDS_DEBIAN={debian_count}")
    print("AURORA_KSQ_SELECTED_SOURCE_RECORDS_NORMALIZED=PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    normalize(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
