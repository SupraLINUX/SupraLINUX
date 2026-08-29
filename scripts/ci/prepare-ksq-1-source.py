#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import email.utils
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests/kde-stack"
ADAPTATIONS = TESTS / "ksq-1-packaging-adaptations.tsv"
DEFAULT_SUFFIX = "~supra26.04.1"

KWALLET_ADAPTATION = "kwallet-pam-compat13-relationship-substvars"
SYNTAX_ADAPTATION = "kf6-syntax-highlighting-deterministic-jinja-order"
SYNTAX_PATCH = ROOT / "packaging/ksq-1/patches/kf6-syntax-highlighting/supralinux-deterministic-jinja-order.patch"


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_1_SOURCE_PREP_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def dpkg_compare(left: str, operator: str, right: str) -> bool:
    return subprocess.run(["dpkg", "--compare-versions", left, operator, right]).returncode == 0


def snapshot_id() -> str:
    path = TESTS / "apt-metadata-snapshot.env"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("AURORA_KSQ_0_APT_SNAPSHOT="):
            value = line.split("=", 1)[1].strip()
            if re.fullmatch(r"\d{8}T\d{6}Z", value):
                return value
    fail(f"invalid snapshot declaration: {path}")


def snapshot_rfc2822(value: str) -> str:
    dt = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return email.utils.format_datetime(dt)


def read_overrides() -> list[dict[str, str]]:
    path = TESTS / "ksq-0-build-dep-overrides.tsv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        expected = ["source_package", "source_version", "field", "from_relation", "to_relation", "reason"]
        if reader.fieldnames != expected:
            fail(f"unexpected override header: {reader.fieldnames}")
        return list(reader)


def read_adaptations() -> list[dict[str, str]]:
    with ADAPTATIONS.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        expected = [
            "source_package",
            "source_version",
            "adaptation_id",
            "kind",
            "implementation_ref",
            "reason",
        ]
        if reader.fieldnames != expected:
            fail(f"unexpected packaging adaptation header: {reader.fieldnames}")
        rows = list(reader)

    seen: set[str] = set()
    for row in rows:
        adaptation_id = row["adaptation_id"]
        if not adaptation_id or adaptation_id in seen:
            fail(f"duplicate or empty packaging adaptation id: {adaptation_id!r}")
        seen.add(adaptation_id)
    return rows


def parse_changelog_header(line: str) -> tuple[str, str, str, str]:
    match = re.fullmatch(r"(\S+) \(([^)]+)\) (\S+); urgency=(\S+)", line.strip())
    if not match:
        fail(f"cannot parse debian/changelog first line: {line!r}")
    return match.group(1), match.group(2), match.group(3), match.group(4)


def apply_override(source_tree: Path, row: dict[str, str]) -> None:
    if row["field"] != "Build-Depends":
        fail(f"unsupported certified override field: {row['field']}")
    control = source_tree / "debian/control"
    text = control.read_text(encoding="utf-8")
    before = row["from_relation"]
    after = row["to_relation"]
    occurrences = text.count(before)
    if occurrences != 1:
        fail(
            f"certified override expected exactly once in {control}: "
            f"{before!r}, found {occurrences}"
        )
    control.write_text(text.replace(before, after, 1), encoding="utf-8")


def restore_kwallet_compat13_substvars(source_tree: Path) -> int:
    control = source_tree / "debian/control"
    text = control.read_text(encoding="utf-8")

    if "debhelper-compat (= 13)" not in text or "debhelper-compat (= 14)" in text:
        fail("kwallet-pam compat-13 packaging adaptation was not applied before substvar restoration")
    if "dh-sequence-plasma" in text:
        fail("kwallet-pam unexpectedly contains dh-sequence-plasma; Ubuntu packaging delta must be preserved")

    common_before = """Package: libpam-kwallet-common
Architecture: all
Depends: socat,
"""
    common_after = """Package: libpam-kwallet-common
Architecture: all
Depends: ${misc:Depends},
         socat,
"""
    pam_before = """Package: libpam-kwallet5
Architecture: any
Depends: kwallet6,
         libpam-kwallet-common (>= ${source:Version}),
         libpam-runtime,
"""
    pam_after = """Package: libpam-kwallet5
Architecture: any
Depends: ${misc:Depends},
         ${qml6:Depends},
         ${shlibs:Depends},
         kwallet6,
         libpam-kwallet-common (>= ${source:Version}),
         libpam-runtime,
"""

    for label, before, after in (
        ("libpam-kwallet-common", common_before, common_after),
        ("libpam-kwallet5", pam_before, pam_after),
    ):
        occurrences = text.count(before)
        if occurrences != 1:
            fail(
                f"kwallet-pam {label} control stanza drift: "
                f"expected certified compat-14 form once, found {occurrences}"
            )
        text = text.replace(before, after, 1)

    required = ("${misc:Depends}", "${qml6:Depends}", "${shlibs:Depends}")
    for token in required:
        if token not in text:
            fail(f"kwallet-pam compat-13 restoration missing {token}")

    control.write_text(text, encoding="utf-8")
    return 3


def apply_syntax_highlighting_repro_patch(source_tree: Path) -> None:
    source_format = source_tree / "debian/source/format"
    if source_format.read_text(encoding="utf-8").strip() != "3.0 (quilt)":
        fail("kf6-syntax-highlighting packaging is no longer 3.0 (quilt)")
    if not SYNTAX_PATCH.is_file():
        fail(f"declared syntax-highlighting patch missing: {SYNTAX_PATCH}")

    target = source_tree / "data/generators/generate_jinja.py"
    text = target.read_text(encoding="utf-8")
    old = "        lang = to_do.pop()\n"
    new = "        lang = min(to_do)\n        to_do.remove(lang)\n"
    if text.count(old) != 1:
        fail(f"kf6-syntax-highlighting generator drift: expected one set.pop() traversal, found {text.count(old)}")
    if new in text:
        fail("kf6-syntax-highlighting deterministic traversal is already present; reassess whether override can be removed")

    patch_dir = source_tree / "debian/patches"
    series = patch_dir / "series"
    patch_dir.mkdir(parents=True, exist_ok=True)
    if series.exists() and series.read_text(encoding="utf-8").strip():
        fail("kf6-syntax-highlighting certified packaging base unexpectedly has a non-empty patch series")

    patch_dest = patch_dir / SYNTAX_PATCH.name
    if patch_dest.exists():
        fail(f"kf6-syntax-highlighting patch destination already exists: {patch_dest}")
    shutil.copyfile(SYNTAX_PATCH, patch_dest)
    series.write_text(SYNTAX_PATCH.name + "\n", encoding="utf-8")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")

    patched = target.read_text(encoding="utf-8")
    if patched.count(new) != 1 or old in patched:
        fail("kf6-syntax-highlighting deterministic traversal was not materialized exactly once")


def apply_packaging_adaptation(source_tree: Path, row: dict[str, str]) -> int:
    adaptation_id = row["adaptation_id"]
    if adaptation_id == KWALLET_ADAPTATION:
        if row["kind"] != "control-relationship-restoration":
            fail(f"{adaptation_id}: unexpected kind {row['kind']!r}")
        expected_ref = "scripts/ci/prepare-ksq-1-source.py#restore_kwallet_compat13_substvars"
        if row["implementation_ref"] != expected_ref:
            fail(f"{adaptation_id}: unexpected implementation ref {row['implementation_ref']!r}")
        return restore_kwallet_compat13_substvars(source_tree)

    if adaptation_id == SYNTAX_ADAPTATION:
        if row["kind"] != "quilt-source-patch":
            fail(f"{adaptation_id}: unexpected kind {row['kind']!r}")
        expected_ref = str(SYNTAX_PATCH.relative_to(ROOT))
        if row["implementation_ref"] != expected_ref:
            fail(f"{adaptation_id}: unexpected implementation ref {row['implementation_ref']!r}")
        apply_syntax_highlighting_repro_patch(source_tree)
        return 0

    fail(f"unsupported packaging adaptation id: {adaptation_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-tree", required=True, type=Path)
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--base-version", required=True)
    parser.add_argument("--suffix", default=DEFAULT_SUFFIX)
    args = parser.parse_args()

    tree = args.source_tree.resolve()
    changelog = tree / "debian/changelog"
    control = tree / "debian/control"
    if not changelog.is_file() or not control.is_file():
        fail(f"not a Debian source tree: {tree}")

    original = changelog.read_text(encoding="utf-8")
    first_line = original.splitlines()[0]
    source, version, _distribution, _urgency = parse_changelog_header(first_line)
    if source != args.expected_source:
        fail(f"source mismatch: expected {args.expected_source}, got {source}")
    if version != args.base_version:
        fail(f"version mismatch for {source}: expected {args.base_version}, got {version}")

    new_version = version + args.suffix
    if not dpkg_compare(new_version, "lt", version):
        fail(f"Supra version must sort below packaging base: {new_version} !< {version}")

    snapshot = snapshot_id()
    applied_overrides: list[dict[str, str]] = []
    for row in read_overrides():
        if row["source_package"] == source and row["source_version"] == version:
            apply_override(tree, row)
            applied_overrides.append(row)

    matching_adaptations = [
        row
        for row in read_adaptations()
        if row["source_package"] == source and row["source_version"] == version
    ]
    restored_substvars = 0
    applied_adaptation_ids: list[str] = []
    for row in matching_adaptations:
        restored_substvars += apply_packaging_adaptation(tree, row)
        applied_adaptation_ids.append(row["adaptation_id"])

    adaptation_ids_value = ",".join(sorted(applied_adaptation_ids)) if applied_adaptation_ids else "-"

    extra_lines: list[str] = []
    if restored_substvars:
        extra_lines.append("  * Restore relationship substvars required by debhelper compat 13.")
    if SYNTAX_ADAPTATION in applied_adaptation_ids:
        extra_lines.append("  * Make Jinja syntax generation order deterministic for reproducible binary output.")

    stanza = (
        f"{source} ({new_version}) resolute; urgency=medium\n\n"
        f"  * SupraLINUX Aurora KSQ-1 rebuild from certified packaging base {version}.\n"
        "  * Apply only packaging adaptations explicitly certified by KSQ-0.\n"
        + ("\n".join(extra_lines) + "\n" if extra_lines else "")
        + "\n"
        f" -- SupraLINUX Build System <build@supralinux.invalid>  {snapshot_rfc2822(snapshot)}\n\n"
    )
    changelog.write_text(stanza + original, encoding="utf-8")

    parsed_version = subprocess.run(
        ["dpkg-parsechangelog", "-l" + str(changelog), "-SVersion"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    if parsed_version != new_version:
        fail(f"dpkg-parsechangelog returned {parsed_version}, expected {new_version}")

    metadata = tree.parent / "supralinux-build-metadata.env"
    metadata.write_text(
        "\n".join(
            [
                f"AURORA_KSQ_1_SOURCE={source}",
                f"AURORA_KSQ_1_PACKAGING_BASE={version}",
                f"AURORA_KSQ_1_VERSION={new_version}",
                f"AURORA_KSQ_1_VERSION_SUFFIX={args.suffix}",
                f"AURORA_KSQ_1_APT_SNAPSHOT={snapshot}",
                f"AURORA_KSQ_1_OVERRIDES_APPLIED={len(applied_overrides)}",
                f"AURORA_KSQ_1_PACKAGING_ADAPTATIONS_APPLIED={len(applied_adaptation_ids)}",
                f"AURORA_KSQ_1_PACKAGING_ADAPTATION_IDS={adaptation_ids_value}",
                f"AURORA_KSQ_1_COMPAT13_SUBSTVARS_RESTORED={restored_substvars}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"AURORA_KSQ_1_SOURCE={source}")
    print(f"AURORA_KSQ_1_PACKAGING_BASE={version}")
    print(f"AURORA_KSQ_1_VERSION={new_version}")
    print(f"AURORA_KSQ_1_OVERRIDES_APPLIED={len(applied_overrides)}")
    print(f"AURORA_KSQ_1_PACKAGING_ADAPTATIONS_APPLIED={len(applied_adaptation_ids)}")
    print(f"AURORA_KSQ_1_PACKAGING_ADAPTATION_IDS={adaptation_ids_value}")
    print(f"AURORA_KSQ_1_COMPAT13_SUBSTVARS_RESTORED={restored_substvars}")
    print("AURORA_KSQ_1_SOURCE_PREP_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
