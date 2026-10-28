#!/usr/bin/env python3
"""Evaluate SupraLINUX-proposed -> campaign milestone promotion; never stable publication."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REQUIRED_GATES = {
    "apt_solvability",
    "clean_install",
    "upgrade_from_ubuntu",
    "dependency_closure",
    "abi_and_plugins",
    "representative_apps",
    "wayland_session",
    "integration_image",
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--integration-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo = json.loads(args.repository.read_text())
    receipt = json.loads(args.integration_receipt.read_text())
    reasons = []

    if repo.get("state") != "PASS":
        reasons.append("repository_not_PASS")
    if repo.get("signed") is not True:
        reasons.append("repository_not_signed")
    if repo.get("activation_eligible") is not True:
        reasons.append("repository_not_activation_eligible")
    if repo.get("stable_publication_authorized") is not False:
        reasons.append("repository_illegally_authorizes_stable")
    if receipt.get("state") != "PASS":
        reasons.append("integration_receipt_not_PASS")
    if receipt.get("suite") != repo.get("suite"):
        reasons.append("suite_mismatch")
    if receipt.get("repository_manifest_sha256") != sha256(args.repository):
        reasons.append("repository_manifest_digest_mismatch")

    gates = receipt.get("gates") or {}
    missing = sorted(REQUIRED_GATES - set(gates))
    failing = sorted(name for name in REQUIRED_GATES if gates.get(name) != "PASS")
    if missing:
        reasons.append("missing_gates=" + ",".join(missing))
    if failing:
        reasons.append("non_PASS_gates=" + ",".join(failing))
    if receipt.get("partial_stack_transition") is not False:
        reasons.append("partial_stack_transition_not_rejected")
    if receipt.get("package_attempts_complete") is not True:
        reasons.append("package_attempts_incomplete")

    state = "PASS" if not reasons else "BLOCKED"
    result = {
        "schema": 1,
        "state": state,
        "kind": "supralinux-proposed-to-milestone-promotion",
        "suite": repo.get("suite"),
        "repository_manifest": str(args.repository),
        "repository_manifest_sha256": sha256(args.repository),
        "integration_receipt": str(args.integration_receipt),
        "integration_receipt_sha256": sha256(args.integration_receipt),
        "required_gates": sorted(REQUIRED_GATES),
        "reasons": reasons,
        "promotion_target": "campaign-milestone",
        "stable_publication_authorized": False,
        "stable_publication_requires_explicit_confirmation": True,
        "package_attempt_consumed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"SupraLINUX-proposed promotion: {state}")
    if state != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
