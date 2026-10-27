#!/usr/bin/env python3
"""Certify the exact unsigned SupraLINUX-proposed repository from retained artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(args: list[str], *, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    if len(args.source_commit) != 40 or any(ch not in "0123456789abcdef" for ch in args.source_commit):
        raise SystemExit("invalid source commit")
    if args.work_dir.exists() or args.evidence_dir.exists():
        raise SystemExit("refusing to reuse proposed certification output paths")
    for command in ("python3", "dpkg-deb", "git"):
        if shutil.which(command) is None:
            raise SystemExit(f"missing proposed certification command: {command}")
    if not args.artifact_root.is_dir():
        raise SystemExit("persistent artifact root is missing")

    resolved = subprocess.check_output(
        ["git", "-C", str(args.checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if resolved != args.source_commit:
        raise SystemExit("proposed certification checkout does not match source commit")
    dirty = subprocess.check_output(
        ["git", "-C", str(args.checkout), "status", "--porcelain", "--untracked-files=normal"],
        text=True,
    )
    if dirty:
        raise SystemExit("proposed certification checkout is not clean")

    retained = json.loads((args.checkout / "manifests/retained-package-artifacts.json").read_text())
    archive_rel = Path(retained["archive_root"])
    if (
        not archive_rel.parts
        or archive_rel.parts[0] != ".artifacts"
        or any(part in {"", ".", ".."} for part in archive_rel.parts)
    ):
        raise SystemExit("invalid retained Frameworks archive root")
    frameworks_archive = args.artifact_root.joinpath(*archive_rel.parts[1:])
    frameworks_index = frameworks_archive / retained["archive_index"]
    if not frameworks_index.is_file() or frameworks_index.is_symlink():
        raise SystemExit("retained Frameworks archive index is missing")
    if sha256(frameworks_index) != retained["archive_index_sha256"]:
        raise SystemExit("retained Frameworks archive index digest mismatch")
    frameworks_payload = json.loads(frameworks_index.read_text())
    if not (
        frameworks_payload.get("artifact_count") == retained.get("artifact_count") == 65
        and frameworks_payload.get("binary_count") == retained.get("binary_count_including_debug")
        and frameworks_payload.get("source_complete_artifact_count") == retained.get("source_complete_artifact_count")
        and frameworks_payload.get("legacy_source_gaps") == retained.get("legacy_source_gaps")
        and frameworks_payload.get("requires_github_for_restore") is False
        and retained.get("requires_github_for_restore") is False
        and len(frameworks_payload.get("items", [])) == retained.get("artifact_count")
    ):
        raise SystemExit("retained Frameworks archive contract mismatch")

    verified_frameworks = 0
    seen_framework_nodes = set()
    for item in frameworks_payload["items"]:
        node = item.get("node")
        digest = item.get("artifact_sha256")
        archive_path = Path(item.get("archive_path", ""))
        if (
            not isinstance(node, str)
            or not node
            or node in seen_framework_nodes
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
            or archive_path.parts != ("sha256", f"{digest}.zip")
        ):
            raise SystemExit("invalid retained Frameworks artifact index entry")
        artifact = frameworks_archive / archive_path
        if not artifact.is_file() or artifact.is_symlink() or sha256(artifact) != digest:
            raise SystemExit(f"retained Frameworks artifact verification failed: {node}")
        seen_framework_nodes.add(node)
        verified_frameworks += 1
    if verified_frameworks != 65:
        raise SystemExit("retained Frameworks artifact count verification mismatch")

    config = json.loads((args.checkout / "manifests/supralinux-proposed.json").read_text())
    if not (
        config.get("state") == "prepared-inactive"
        and config.get("active") is False
        and config.get("current_plasma_campaign_unchanged") is True
        and config.get("repository_policy", {}).get("signed_before_activation") is True
        and config.get("repository_policy", {}).get("stable_publication_authorized") is False
    ):
        raise SystemExit("SupraLINUX-proposed is not in prepared-inactive certification state")

    args.work_dir.mkdir(parents=True, mode=0o700)
    args.evidence_dir.mkdir(parents=True, mode=0o700)
    plan = args.evidence_dir / "plan.json"
    repository = args.work_dir / "repository"
    repository_manifest = args.evidence_dir / "repository.json"

    run(
        ["python3", "scripts/plan-supralinux-proposed.py", "--output", str(plan)],
        cwd=args.checkout,
    )
    plan_payload = json.loads(plan.read_text())
    if (
        plan_payload.get("state") != "PASS"
        or plan_payload.get("package_attempt_consumed") is not False
        or plan_payload.get("stable_publication_authorized") is not False
    ):
        raise SystemExit("invalid SupraLINUX-proposed transaction plan")

    run(
        [
            "python3",
            "scripts/build-supralinux-proposed.py",
            "--plan", str(plan),
            "--artifact-root", str(args.artifact_root),
            "--output", str(repository),
            "--manifest", str(repository_manifest),
            "--unsigned-certification",
        ],
        cwd=args.checkout,
    )
    repo_payload = json.loads(repository_manifest.read_text())
    if not (
        repo_payload.get("state") == "PASS"
        and repo_payload.get("candidate_count") == plan_payload.get("candidate_count")
        and repo_payload.get("signed") is False
        and repo_payload.get("activation_eligible") is False
        and repo_payload.get("stable_publication_authorized") is False
        and repo_payload.get("package_attempt_consumed") is False
        and repo_payload.get("canonical_package_state_effect") == "none"
    ):
        raise SystemExit("unsigned proposed repository returned an invalid certification receipt")

    planned = {
        (row["node"], row["artifact_sha256"])
        for row in plan_payload["candidates"]
    }
    built = {
        (row["node"], row["artifact_sha256"])
        for row in repo_payload["candidates"]
    }
    if built != planned:
        raise SystemExit("built proposed candidate identity differs from the exact plan")

    suite = plan_payload["suite"]
    release = repository / "dists" / suite / "Release"
    packages = repository / "dists" / suite / "main" / "binary-amd64" / "Packages"
    sources = repository / "dists" / suite / "main" / "source" / "Sources"
    for path in (release, packages, sources):
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"proposed repository index missing: {path}")
    for forbidden in (
        repository / "dists" / suite / "InRelease",
        repository / "dists" / suite / "Release.gpg",
    ):
        if forbidden.exists():
            raise SystemExit("unsigned certification unexpectedly produced repository signatures")

    result = {
        "schema": 1,
        "state": "PASS",
        "kind": "supralinux-proposed-content-certification",
        "source_commit": args.source_commit,
        "suite": suite,
        "candidate_count": plan_payload["candidate_count"],
        "excluded_count": len(plan_payload.get("excluded", [])),
        "frameworks_pass_nodes": plan_payload["base_stack"]["frameworks_pass_nodes"],
        "frameworks_archive_index_sha256": sha256(frameworks_index),
        "frameworks_artifacts_verified": verified_frameworks,
        "frameworks_requires_github_for_restore": False,
        "plan_sha256": sha256(plan),
        "repository_manifest_sha256": sha256(repository_manifest),
        "packages_sha256": sha256(packages),
        "sources_sha256": sha256(sources),
        "release_sha256": sha256(release),
        "signed": False,
        "activation_eligible": False,
        "repository_active": False,
        "stable_publication_authorized": False,
        "canonical_package_state_effect": "none",
        "package_attempt_consumed": False,
        "sbuild_invoked": False,
        "vm_created": False,
        "jit_invoked": False,
        "artifact_root_persistent": True,
        "network_required": False,
    }
    (args.evidence_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(
        "SupraLINUX-proposed content certification: PASS; "
        f"candidates={result['candidate_count']} frameworks={result['frameworks_pass_nodes']}"
    )


if __name__ == "__main__":
    main()
