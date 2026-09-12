#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests" / "kde-tier1-package-campaign.json"
TIER1 = ROOT / "manifests" / "kde-frameworks-tier1.json"
RUNNER = ROOT / "scripts" / "run-kde-tier1-package-preflight.sh"
SCOPE = ROOT / "scripts" / "kde-tier1-package-preflight-needed.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "kde-tier1-package-preflight.yml"
DOC = ROOT / "docs" / "kde-tier1-package-batch1.md"

SIGNING_KEY_SHA256 = "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d"
ATTEMPT1_RUN = 34709829162
ATTEMPT1_COMMIT = "50611225422b05803ee49d8d5fc8ff4f84a21d99"
ATTEMPT2_RUN = 34710627400
ATTEMPT2_COMMIT = "3fa96423bb01b8a7cd63a62ab5947cf7ef57b482"

EXPECTED = {
    "kcodecs": {
        "source_sha256": "a42c79ff3237b73789d1c63cdfd848c0d59671ce5e93723a2efa128f00cb3450",
        "symbols_sha256": "35f6b7b6885b3db41bcce95b99610b2e917e1b4e13d5ba7e801b93dd47c4f8c7",
        "symbols_tree": "debian",
        "symbols_reference": "debian-sid",
        "attempt1": (103596438631, 10302917591, "6fcf23a69991e453d3563d580aa63fa082c27ce8490ad52dd9e125ee41cd8f6f"),
        "attempt2": (103598645411, 10303621032, "722b83f04fadc67337129f6435547e0c9b3ad6b8b3d02655be258d86cb62e6a6", "sbuild", "dpkg-gensymbols", "8/8 PASS"),
        "required_build_deps": ["qt6-base-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
        "test_rule": "dh_auto_test",
    },
    "kdbusaddons": {
        "source_sha256": "063ef80460f76d86dc4b033ef04b65b69ba82ee0de410440fe609465e7f5a997",
        "symbols_sha256": "03b48faa6b7c5b400f3a165c38c4c5e7e7fc454a0b099ef1ad776b3809851683",
        "symbols_tree": "ubuntu",
        "symbols_reference": "ubuntu-resolute",
        "attempt1": (103596438606, 10303285563, "2a581e9f4c01c15c611b5b3d3a98343504177f1d52fb2225f92ce3c6428f54ed"),
        "attempt2": (103598645369, 10303366682, "75879797c369c29c00eb6fa647cca9958645eb80437531f7dfee42fe99327763", "artifact-contract", "multi-arch-normalization", "3/3 PASS"),
        "required_build_deps": ["dbus-daemon <!nocheck>", "qt6-base-dev (>= 6.9.0~)", "qt6-base-private-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
        "test_rule": "dbus-run-session dh_auto_test",
    },
    "threadweaver": {
        "source_sha256": "e5400968a41820393e76190ab5dbb276c09513263d1b185d64b40f82dcd9b457",
        "symbols_sha256": "a7403ee234e24d20f20502ed4a07b13ef265ec285cd5fb2b44709dfea39907b7",
        "symbols_tree": "ubuntu",
        "symbols_reference": "ubuntu-resolute",
        "attempt1": (103596438491, 10303265649, "0b47374207ae54632c4ba9594eedbcc72d46eed552696b608110ebb5bce6acb6"),
        "attempt2": (103598645228, 10302524114, "5582b94c2e134011297a51fd02183464253c0c5f43678a79fd256f128b2f2d6f", "artifact-contract", "multi-arch-normalization", "8/8 PASS"),
        "required_build_deps": ["qt6-base-dev (>= 6.9.0~)"],
        "test_rule": "dh_auto_test",
    },
}

errors: list[str] = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot load {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(value, dict):
        raise SystemExit(f"{path.relative_to(ROOT)} must contain an object")
    return value

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

campaign = load(CAMPAIGN)
tier1 = load(TIER1)
runner = read(RUNNER)
scope = read(SCOPE)
workflow = read(WORKFLOW)
doc = read(DOC)

require(campaign.get("schema") == 1, "Campaign schema must remain 1")
require(campaign.get("authority") == "kde-upstream", "Campaign authority must remain KDE upstream")
require(campaign.get("frameworks_series") == "6.30.0", "Campaign must target Frameworks 6.30.0")
require(campaign.get("state") == "remediation-pending-build", "Batch 1 must be remediation-pending-build before attempt 3")

first = campaign.get("first_attempt", {})
require(first.get("workflow_run") == ATTEMPT1_RUN and first.get("commit") == ATTEMPT1_COMMIT and first.get("result") == "FAIL", "Attempt 1 summary mismatch")
second = campaign.get("second_attempt", {})
require(second.get("workflow_run") == ATTEMPT2_RUN and second.get("commit") == ATTEMPT2_COMMIT and second.get("result") == "FAIL", "Attempt 2 summary mismatch")
require("autotest" in second.get("summary", "").lower() and "passed" in second.get("summary", "").lower(), "Attempt 2 summary must state that KDE tests passed")

signing = campaign.get("shared_packaging_inputs", {}).get("signing_key", {})
require(signing.get("sha256") == SIGNING_KEY_SHA256, "Signing-key hash mismatch")
require(signing.get("purpose") == "debian-watch-v5-pgp-verification", "Signing-key purpose mismatch")

nodes = campaign.get("nodes", {})
require(set(nodes) == set(EXPECTED), "Batch 1 node set changed")
tier1_nodes = {x.get("id"): x for x in tier1.get("nodes", []) if isinstance(x, dict)}

for node_id, expected in EXPECTED.items():
    node = nodes.get(node_id, {})
    require(node.get("state") == "remediation-pending-build", f"{node_id}: remediation state mismatch")
    require(node.get("last_result") == "FAIL", f"{node_id}: current historical result must remain FAIL before attempt 3")
    require(node.get("package_version") == "6.30.0-0supralinux3", f"{node_id}: candidate revision must be -0supralinux3")
    require(node.get("source_sha256") == expected["source_sha256"], f"{node_id}: source hash changed")
    symbols = node.get("symbols", {})
    require(symbols.get("sha256") == expected["symbols_sha256"], f"{node_id}: symbols hash mismatch")
    require(symbols.get("tree_provider") == expected["symbols_tree"], f"{node_id}: symbols provider-tree mismatch")
    require(symbols.get("reference") == expected["symbols_reference"], f"{node_id}: symbols reference label mismatch")

    evidence = node.get("evidence", [])
    require(len(evidence) == 2, f"{node_id}: exactly two historical attempts expected")
    if len(evidence) == 2:
        a1, a2 = evidence
        j1, art1, digest1 = expected["attempt1"]
        require(a1.get("result") == "FAIL" and a1.get("workflow_run") == ATTEMPT1_RUN and a1.get("job_id") == j1, f"{node_id}: attempt 1 identity mismatch")
        require(a1.get("artifact_id") == art1 and a1.get("artifact_sha256") == digest1, f"{node_id}: attempt 1 artifact mismatch")
        require(a1.get("attempted_package_version") == "6.30.0-0supralinux1", f"{node_id}: attempt 1 version mismatch")
        require(a1.get("autotests_reached") is False, f"{node_id}: attempt 1 must not claim autotests")

        j2, art2, digest2, stage2, sub2, tests2 = expected["attempt2"]
        require(a2.get("result") == "FAIL" and a2.get("workflow_run") == ATTEMPT2_RUN and a2.get("job_id") == j2, f"{node_id}: attempt 2 identity mismatch")
        require(a2.get("artifact_id") == art2 and a2.get("artifact_sha256") == digest2, f"{node_id}: attempt 2 artifact mismatch")
        require(a2.get("attempted_package_version") == "6.30.0-0supralinux2", f"{node_id}: attempt 2 version mismatch")
        require(a2.get("failure_stage") == stage2 and a2.get("failure_substage") == sub2, f"{node_id}: attempt 2 failure-stage mismatch")
        require(a2.get("autotests_reached") is True and a2.get("autotests") == tests2, f"{node_id}: attempt 2 test evidence mismatch")

    source_node = tier1_nodes.get(node_id, {})
    require(source_node.get("source_sha256") == expected["source_sha256"], f"{node_id}: source/canonical hash mismatch")
    require(source_node.get("depends_on") == ["extra-cmake-modules"], f"{node_id}: KDE predecessor changed")

    pkg = ROOT / "packages" / "kde" / node_id / "debian"
    control = read(pkg / "control")
    rules = read(pkg / "rules")
    changelog = read(pkg / "changelog")
    key = pkg / "upstream" / "signing-key.asc"

    require(changelog.startswith(f"kf6-{node_id} (6.30.0-0supralinux3) resolute;"), f"{node_id}: changelog candidate revision mismatch")
    require("6.30.0-0supralinux2" in changelog and "6.30.0-0supralinux1" in changelog, f"{node_id}: historical revisions missing from changelog")
    require("Standards-Version: 4.7.3" in control, f"{node_id}: Standards-Version must match Resolute policy baseline")
    require("Standards-Version: 4.7.4" not in control, f"{node_id}: stale Standards-Version remains")
    require("reuse" not in control.lower() and "reuse lint" not in rules, f"{node_id}: invalid REUSE gate returned")
    require("-DBUILD_TESTING=ON" in rules and expected["test_rule"] in rules, f"{node_id}: KDE tests are not preserved")
    require(key.is_file(), f"{node_id}: watch signing key missing")
    if key.is_file():
        require(sha256(key) == SIGNING_KEY_SHA256, f"{node_id}: signing-key bytes differ from retained Debian reference")
    for dep in ("debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)"):
        require(dep in control, f"{node_id}: packaging dependency missing: {dep}")
    for dep in expected["required_build_deps"]:
        require(dep in control, f"{node_id}: provider dependency missing: {dep}")

for token in (
    'SYMBOLS_REFERENCE_TREE',
    'trees/${SYMBOLS_REFERENCE_TREE}/${NODE}/debian/${SYMBOLS_FILE}',
    'value in {"", "no"}',
    'SIGNING_KEY_SHA256',
    'lintian --fail-on error',
    'downstream_eligible=yes',
    'dpkg-source -b',
    '--chroot-mode=unshare',
):
    require(token in runner, f"Generic runner missing attempt-3 invariant: {token}")
require("dpkg-buildpackage -S" not in runner and "reuse lint" not in runner, "Runner reintroduced obsolete source/REUSE behavior")

for token in ("kcodecs|kdbusaddons|threadweaver", 'packages/kde/"${NODE}"/*', "manifests/kde-tier1-package-campaign.json"):
    require(token in scope, f"Batch scope missing invariant: {token}")
require("docs/" not in scope, "Docs-only changes must not rebuild packages")

for token in ("fail-fast: false", "max-parallel: 3", "- kcodecs", "- kdbusaddons", "- threadweaver", "10298635300", "10301938362"):
    require(token in workflow, f"Batch workflow missing invariant: {token}")

for token in (
    "34709829162", "34710627400", "10303621032", "10303366682", "10302524114",
    "8/8", "3/3", "35f6b7b6885b3db41bcce95b99610b2e917e1b4e13d5ba7e801b93dd47c4f8c7",
    SIGNING_KEY_SHA256, "6.30.0-0supralinux3",
):
    require(token in doc, f"Batch documentation missing evidence/token {token}")
require("not blocked" in doc.lower() or "none is blocked" in doc.lower(), "Documentation must preserve FAIL vs BLOCKED semantics")
require("std::format" in doc, "Documentation must record the KCodecs implementation-symbol observation")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 batch 1 attempt-3 preparation validation: PASS")
print("Attempts 1/2 remain historical FAIL; candidate revision: 6.30.0-0supralinux3")
print("KDE attempt-2 tests: kcodecs 8/8 PASS; kdbusaddons 3/3 PASS; threadweaver 8/8 PASS")
