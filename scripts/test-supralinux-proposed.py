#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "scripts/plan-supralinux-proposed.py"
BUILDER = ROOT / "scripts/build-supralinux-proposed.py"
PROMOTER = ROOT / "scripts/evaluate-supralinux-proposed-promotion.py"
CONFIG = ROOT / "manifests/supralinux-proposed.json"
PLASMA = ROOT / "manifests/kde-plasma-package-build.json"

with tempfile.TemporaryDirectory() as td:
    plan = Path(td) / "plan.json"
    subprocess.run(
        ["python3", str(PLANNER), "--output", str(plan)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(plan.read_text())
    plasma = json.loads(PLASMA.read_text())
    expected = {
        node
        for node, record in plasma["nodes"].items()
        if record.get("state") == "PASS"
        and not record.get("compatibility_hold")
        and any(item.get("state") == "PASS" for item in record.get("attempts", []))
    }
    actual = {item["node"] for item in payload["candidates"]}
    assert actual == expected, (sorted(expected - actual), sorted(actual - expected))
    assert "drkonqi" not in actual
    assert "kglobalacceld" not in actual
    assert "libksysguard" not in actual
    assert payload["stable_publication_authorized"] is False
    assert payload["base_stack"]["frameworks_pass_nodes"] == 65

builder = BUILDER.read_text()
for token in (
    "exactly one artifact ZIP",
    "artifact digest drift",
    "candidate version drift",
    "candidate architecture drift",
    "candidate source drift",
    "candidate binary set mismatch",
    "Checksums-Sha256",
    "apt-ftparchive",
    "Packages.gz",
    "Sources.gz",
    "InRelease",
    "Release.gpg",
    "signed proposed repositories require --signing-key",
    '"stable_publication_authorized": False',
):
    assert token in builder, f"proposed builder missing contract: {token}"
for forbidden in ("trusted=yes", "allow-unauthenticated"):
    assert forbidden not in builder, f"unsafe proposed repository behavior: {forbidden}"

for token in (
    'raw.split(":", 1)',
    'gzip.GzipFile(fileobj=raw, mode="wb", mtime=0)',
):
    assert token in builder, f"proposed builder misses reproducible/parser contract: {token}"

promoter = PROMOTER.read_text()
for token in (
    "apt_solvability",
    "clean_install",
    "upgrade_from_ubuntu",
    "dependency_closure",
    "abi_and_plugins",
    "representative_apps",
    "wayland_session",
    "integration_image",
    '"promotion_target": "campaign-milestone"',
    '"stable_publication_authorized": False',
    '"stable_publication_requires_explicit_confirmation": True',
):
    assert token in promoter, f"promotion evaluator missing gate: {token}"

config = json.loads(CONFIG.read_text())
assert config["state"] == "prepared-inactive"
assert config["active"] is False
assert config["current_plasma_campaign_unchanged"] is True
assert config["repository_policy"]["signed_before_activation"] is True
assert config["promotion"]["proposed_to_stable"] == "never automatic"

print(
    "SupraLINUX-proposed contract: PASS; "
    f"eligible_plasma_candidates={len(expected)}"
)
