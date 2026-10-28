#!/usr/bin/env python3
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build-ubuntu-campaign-rootfs.py"
MANIFEST = ROOT / "manifests/ubuntu-campaign-snapshot.json"

source = SCRIPT.read_text()
ast.parse(source)

for token in (
    'SNAPSHOT_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")',
    '"--skip=cleanup/apt/lists"',
    'f\'--aptopt=APT::Snapshot "{args.snapshot_id}"\'',
    '"--keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg"',
    'env["SOURCE_DATE_EPOCH"] = str(epoch)',
    '"apt_lists_retained": True',
    '"apt_update": False',
    '"apt_distupgrade": False',
    '"frameworks_and_qt_sdk_preinstalled": False',
):
    assert token in source, f"missing frozen-rootfs contract: {token}"

for forbidden in (
    "allow-unauthenticated",
    "trusted=yes",
    "Check-Valid-Until \"false\"",
):
    assert forbidden not in source, f"unsafe frozen-rootfs construct: {forbidden}"

manifest = json.loads(MANIFEST.read_text())
assert manifest["state"] == "prepared-inactive"
assert manifest["activation_scope"] == "future-campaign-boundary-only"
assert manifest["current_plasma_campaign_unchanged"] is True
assert manifest["snapshot_id"] is None
assert manifest["rootfs"]["retain_apt_lists"] is True
assert manifest["rootfs"]["frameworks_and_qt_sdk_preinstalled"] is False
assert manifest["sbuild_policy_after_certification"] == {
    "apt_update": False,
    "apt_distupgrade": False,
    "extra_package_repository_update": True,
}
assert manifest["certification"]["same_snapshot_two_build_sha256_match"] is True

print("Frozen Ubuntu campaign snapshot mechanism: PASS")
