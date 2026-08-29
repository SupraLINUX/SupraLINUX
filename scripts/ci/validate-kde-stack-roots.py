#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / "packages/supralinux-desktop/debian/control"
ROOTS = ROOT / "tests/kde-stack/aurora-package-roots.tsv"
PLASMA = ROOT / "tests/kde-stack/plasma-6.7.4-sources.tsv"
FRAMEWORKS = ROOT / "tests/kde-stack/frameworks-6.29.0-sources.tsv"


def fail(message: str) -> "NoReturn":
    print(f"AURORA_KSQ_0_ROOTS_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_stanza(text: str, package: str) -> dict[str, str]:
    for raw_stanza in re.split(r"\n\s*\n", text.strip()):
        fields: dict[str, str] = {}
        current: str | None = None
        for line in raw_stanza.splitlines():
            if line.startswith((" ", "\t")):
                if current:
                    fields[current] += " " + line.strip()
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            current = key
            fields[key] = value.strip()
        if fields.get("Package") == package:
            return fields
    fail(f"package stanza not found: {package}")


def relation_packages(value: str) -> list[str]:
    result: list[str] = []
    for item in value.split(","):
        item = item.strip()
        if not item or item.startswith("${"):
            continue
        if "|" in item:
            fail(f"unclassified alternative dependency in supralinux-desktop: {item}")
        name = re.split(r"\s|\(", item, maxsplit=1)[0]
        name = name.split(":", 1)[0]
        if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", name):
            fail(f"unable to parse dependency token: {item}")
        result.append(name)
    return result


def manifest_modules(path: Path, expected_version: str) -> set[str]:
    if not path.is_file():
        fail(f"missing source manifest: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["module", "version", "sha256"]:
            fail(f"unexpected source-manifest header: {path}")
        modules: set[str] = set()
        for row in reader:
            if row["version"] != expected_version:
                fail(f"mixed version in {path}: {row['module']}={row['version']}")
            if row["module"] in modules:
                fail(f"duplicate source module in {path}: {row['module']}")
            modules.add(row["module"])
    return modules


fields = parse_stanza(CONTROL.read_text(encoding="utf-8"), "supralinux-desktop")
expected: set[tuple[str, str]] = set()
for relation in ("Depends", "Recommends"):
    for package in relation_packages(fields.get(relation, "")):
        expected.add((package, relation))

if not ROOTS.is_file():
    fail(f"missing package-root classification: {ROOTS}")

with ROOTS.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    required_header = ["binary_package", "relation", "candidate_family", "upstream_module", "ksq_action"]
    if reader.fieldnames != required_header:
        fail(f"unexpected roots header: {reader.fieldnames}")
    rows = list(reader)

actual: set[tuple[str, str]] = set()
for row in rows:
    key = (row["binary_package"], row["relation"])
    if key in actual:
        fail(f"duplicate package root: {key[0]} / {key[1]}")
    actual.add(key)

missing = sorted(expected - actual)
extra = sorted(actual - expected)
if missing:
    fail("unclassified supralinux-desktop roots: " + ", ".join(f"{p}[{r}]" for p, r in missing))
if extra:
    fail("stale package-root rows: " + ", ".join(f"{p}[{r}]" for p, r in extra))

plasma_modules = manifest_modules(PLASMA, "6.7.4")
framework_modules = manifest_modules(FRAMEWORKS, "6.29.0")
allowed = {
    ("supralinux", "retain"),
    ("plasma-6.7.4", "rebuild"),
    ("frameworks-6.29.0", "rebuild"),
    ("gear-review", "defer-gear"),
    ("kde-adjacent-ubuntu", "compat-test"),
    ("ubuntu-platform", "keep-ubuntu"),
}

for row in rows:
    family = row["candidate_family"]
    action = row["ksq_action"]
    module = row["upstream_module"]
    if (family, action) not in allowed:
        fail(f"invalid family/action for {row['binary_package']}: {family}/{action}")
    if family == "plasma-6.7.4" and module not in plasma_modules:
        fail(f"Plasma root maps to unknown 6.7.4 module: {row['binary_package']} -> {module}")
    if family == "frameworks-6.29.0" and module not in framework_modules:
        fail(f"Frameworks root maps to unknown 6.29.0 module: {row['binary_package']} -> {module}")
    if family not in {"plasma-6.7.4", "frameworks-6.29.0"} and module != "-":
        fail(f"non-release-set root unexpectedly names upstream module: {row['binary_package']} -> {module}")

counts = Counter(row["candidate_family"] for row in rows)
print(f"AURORA_KSQ_0_ROOTS_TOTAL={len(rows)}")
for family in sorted(counts):
    print(f"AURORA_KSQ_0_ROOTS_{family.upper().replace('-', '_').replace('.', '_')}={counts[family]}")
print("AURORA_KSQ_0_ROOTS_SUCCESS")
