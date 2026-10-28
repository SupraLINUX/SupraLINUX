#!/usr/bin/env python3
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build-reviewed-predecessor-apt-view.py"

source = SCRIPT.read_text()
ast.parse(source)

for token in (
    'admission.get("state") != "PASS"',
    'admission.get("cache_only") is not True',
    'sha256(source) != expected_sha',
    'deb_field(source, "Package")',
    'deb_field(source, "Version")',
    'deb_field(source, "Architecture")',
    'deb_field(source, "Source").split(" ", 1)[0]',
    '["apt-ftparchive", "packages", "pool"]',
    '["apt-ftparchive", "release", "."]',
    '"allows_unselected_milestone_packages": False',
    '"package_attempt_consumed": False',
    '"publication_role": "none"',
):
    assert token in source, f"missing exact APT-view contract: {token}"

for forbidden in (
    "repo/pool/*.deb",
    "trusted=yes",
    "allow-unauthenticated",
    "apt-get install",
    "sbuild ",
):
    assert forbidden not in source, f"APT-view builder crosses scope: {forbidden}"

print("Exact reviewed predecessor APT-view mechanism: PASS")
