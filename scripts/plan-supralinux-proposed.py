#!/usr/bin/env python3
"""Plan the exact Plasma PASS set eligible for SupraLINUX-proposed."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def latest_pass(record: dict) -> dict | None:
    passes = [item for item in record.get("attempts", []) if item.get("state") == "PASS"]
    if not passes:
        return None
    return max(passes, key=lambda item: int(item["attempt"]))


def has_verified_offline_artifact(record: dict, attempt: dict) -> bool:
    evidence = record.get("evidence") or {}
    local = evidence.get("local_retention") or {}
    return (
        attempt.get("artifact_origin") == "sealed-host-package-export"
        and bool(attempt.get("artifact_sha256"))
        and bool(local.get("archive_root"))
        and local.get("source_complete") is True
        and local.get("changes_complete") is True
        and local.get("buildinfo_verified") is True
        and local.get("artifact_zip_sha256_verified") is True
        and local.get("offline_restore_verified") is True
        and local.get("requires_github_for_restore") is False
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("manifests/kde-plasma-package-build.json"),
    )
    parser.add_argument(
        "--frameworks-base",
        type=Path,
        default=Path("manifests/retained-package-artifacts.json"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--nodes", nargs="*")
    args = parser.parse_args()

    plasma = json.loads(args.manifest.read_text())
    frameworks = json.loads(args.frameworks_base.read_text())
    requested = set(args.nodes or [])
    if requested - set(plasma["nodes"]):
        raise SystemExit(f"unknown requested nodes: {sorted(requested - set(plasma['nodes']))}")

    candidates = []
    excluded = []
    for node, record in sorted(plasma["nodes"].items()):
        if requested and node not in requested:
            continue
        reasons = []
        if record.get("state") != "PASS":
            reasons.append(f"state={record.get('state')}")
        if record.get("compatibility_hold"):
            reasons.append("compatibility_hold")
        attempt = latest_pass(record)
        if attempt is None:
            reasons.append("no_PASS_attempt")
        evidence = record.get("evidence") or {}
        if attempt is not None:
            for key in (
                "artifact_sha256",
                "result_path",
                "result_sha256",
                "source_commit",
            ):
                if not attempt.get(key):
                    reasons.append(f"attempt_missing_{key}")
                if evidence.get(key) != attempt.get(key):
                    reasons.append(f"evidence_attempt_{key}_mismatch")

            artifact_id = attempt.get("artifact_id")
            if evidence.get("artifact_id") != artifact_id:
                reasons.append("evidence_attempt_artifact_id_mismatch")
            if artifact_id is None:
                if not has_verified_offline_artifact(record, attempt):
                    reasons.append("no_verified_artifact_locator")
            elif not isinstance(artifact_id, int) or artifact_id <= 0:
                reasons.append("invalid_artifact_id")
        binaries = record.get("binary_packages") or {}
        if not binaries:
            reasons.append("no_binary_packages")

        if reasons:
            excluded.append({"node": node, "reasons": sorted(set(reasons))})
            continue

        local = evidence.get("local_retention") or {}
        candidates.append(
            {
                "node": node,
                "source_package": record["source_package"],
                "version": record["version"],
                "architecture": "amd64",
                "binary_packages": dict(sorted(binaries.items())),
                "attempt": int(attempt["attempt"]),
                "artifact_id": (
                    int(attempt["artifact_id"])
                    if attempt.get("artifact_id") is not None
                    else None
                ),
                "artifact_sha256": attempt["artifact_sha256"],
                "result_path": attempt["result_path"],
                "result_sha256": attempt["result_sha256"],
                "source_commit": attempt["source_commit"],
                "host_evidence_manifest_sha256": attempt.get(
                    "host_evidence_manifest_sha256"
                ),
                "retention": {
                    "archive_root": local.get("archive_root"),
                    "archive_index_sha256": local.get("archive_index_sha256"),
                    "source_complete": local.get("source_complete"),
                    "changes_complete": local.get("changes_complete"),
                    "buildinfo_verified": local.get("buildinfo_verified"),
                    "artifact_zip_sha256_verified": local.get(
                        "artifact_zip_sha256_verified"
                    ),
                    "offline_restore_verified": local.get("offline_restore_verified"),
                    "requires_github_for_restore": local.get(
                        "requires_github_for_restore"
                    ),
                },
            }
        )

    if requested and excluded:
        raise SystemExit(
            "requested proposed transaction includes ineligible nodes: "
            + json.dumps(excluded, sort_keys=True)
        )
    if not candidates:
        raise SystemExit("no eligible Plasma PASS candidates for proposed")

    if frameworks.get("artifact_count") != 65:
        raise SystemExit("Frameworks base is not the closed 65-node milestone")
    if not str(frameworks.get("result", "")).startswith("PASS"):
        raise SystemExit("Frameworks retained base is not PASS")

    result = {
        "schema": 1,
        "state": "PASS",
        "kind": "supralinux-proposed-transaction-plan",
        "suite": "resolute-supralinux-proposed",
        "architecture": "amd64",
        "base_stack": {
            "ubuntu": "resolute",
            "frameworks_manifest": str(args.frameworks_base),
            "frameworks_manifest_sha256": sha256(args.frameworks_base),
            "frameworks_pass_nodes": 65,
            "frameworks_role": "separate admitted base repository",
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
        "excluded": excluded,
        "selection_policy": "state PASS + PASS attempt + canonical evidence match + no compatibility hold",
        "canonical_state_effect": "none",
        "package_attempt_consumed": False,
        "stable_publication_authorized": False,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
