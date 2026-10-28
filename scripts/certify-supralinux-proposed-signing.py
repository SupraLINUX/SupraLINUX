#!/usr/bin/env python3
"""Certify signed SupraLINUX-proposed metadata with an ephemeral non-production key."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, stdout=None) -> None:
    subprocess.run(args, cwd=cwd, env=env, stdout=stdout, check=True)


def signing_fingerprint(env: dict[str, str], cwd: Path) -> str:
    output = subprocess.check_output(
        ["gpg", "--batch", "--with-colons", "--list-secret-keys"],
        cwd=cwd,
        env=env,
        text=True,
    )
    values = [line.split(":")[9] for line in output.splitlines() if line.startswith("fpr:")]
    if len(values) != 1:
        raise SystemExit(f"expected one ephemeral signing fingerprint, found {len(values)}")
    return values[0]


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
        raise SystemExit("refusing to reuse proposed signing certification output paths")
    for command in ("python3", "dpkg-deb", "git", "gpg", "gpgv"):
        if shutil.which(command) is None:
            raise SystemExit(f"missing proposed signing certification command: {command}")
    if not args.artifact_root.is_dir() or args.artifact_root.is_symlink():
        raise SystemExit("persistent artifact root is missing or invalid")

    resolved = subprocess.check_output(
        ["git", "-C", str(args.checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if resolved != args.source_commit:
        raise SystemExit("proposed signing certification checkout does not match source commit")
    dirty = subprocess.check_output(
        ["git", "-C", str(args.checkout), "status", "--porcelain", "--untracked-files=normal"],
        text=True,
    )
    if dirty:
        raise SystemExit("proposed signing certification checkout is not clean")

    sealed = json.loads(
        (args.checkout / "manifests/supralinux-proposed-content-certification.json").read_text()
    )
    if not (
        sealed.get("state") == "PASS"
        and sealed.get("rollout", {}).get("phase_completed") == "unsigned-content-certification"
        and sealed.get("invariants", {}).get("signed") is False
        and sealed.get("invariants", {}).get("activation_eligible") is False
        and sealed.get("invariants", {}).get("repository_active") is False
        and sealed.get("invariants", {}).get("stable_publication_authorized") is False
    ):
        raise SystemExit("sealed unsigned proposed content certification is not reusable")

    evidence_relative = Path(sealed["certification"]["evidence_path"])
    if (
        not evidence_relative.parts
        or evidence_relative.is_absolute()
        or any(part in {"", ".", ".."} for part in evidence_relative.parts)
    ):
        raise SystemExit("invalid sealed proposed content evidence path")
    sealed_evidence_path = args.checkout / evidence_relative
    if not sealed_evidence_path.is_file() or sealed_evidence_path.is_symlink():
        raise SystemExit("sealed proposed content evidence is missing")
    if sha256(sealed_evidence_path) != sealed["certification"]["result_sha256"]:
        raise SystemExit("sealed proposed content evidence digest mismatch")
    sealed_result = json.loads(sealed_evidence_path.read_text())
    if not (
        sealed_result.get("state") == "PASS"
        and sealed_result.get("signed") is False
        and sealed_result.get("candidate_count") == 24
        and sealed_result.get("frameworks_pass_nodes") == 65
        and sealed_result.get("stable_publication_authorized") is False
    ):
        raise SystemExit("sealed proposed content result contract mismatch")

    config = json.loads((args.checkout / "manifests/supralinux-proposed.json").read_text())
    if not (
        config.get("state") == "prepared-inactive"
        and config.get("active") is False
        and config.get("current_plasma_campaign_unchanged") is True
        and config.get("repository_policy", {}).get("signed_before_activation") is True
        and config.get("repository_policy", {}).get("stable_publication_authorized") is False
    ):
        raise SystemExit("SupraLINUX-proposed is not in prepared-inactive signing state")

    args.work_dir.mkdir(parents=True, mode=0o700)
    args.evidence_dir.mkdir(parents=True, mode=0o700)
    plan = args.evidence_dir / "plan.json"
    repository = args.work_dir / "repository"
    repository_manifest = args.evidence_dir / "repository.json"
    gnupg_home = args.work_dir / "gnupg"
    gnupg_home.mkdir(mode=0o700)

    run(["python3", "scripts/plan-supralinux-proposed.py", "--output", str(plan)], cwd=args.checkout)
    if sha256(plan) != sealed["certification"]["plan_sha256"]:
        raise SystemExit("signed certification plan differs from sealed unsigned content plan")
    plan_payload = json.loads(plan.read_text())
    if not (
        plan_payload.get("state") == "PASS"
        and plan_payload.get("candidate_count") == sealed["coverage"]["plasma_candidates"] == 24
        and plan_payload.get("base_stack", {}).get("frameworks_pass_nodes") == 65
        and plan_payload.get("stable_publication_authorized") is False
    ):
        raise SystemExit("invalid signed certification transaction plan")

    env = os.environ.copy()
    env["GNUPGHOME"] = str(gnupg_home)
    identity = "SupraLINUX proposed certification <certification@supralinux.invalid>"
    run(
        ["gpg", "--batch", "--passphrase", "", "--quick-generate-key", identity, "ed25519", "sign", "0"],
        cwd=args.checkout,
        env=env,
    )
    fingerprint = signing_fingerprint(env, args.checkout)

    public_key = args.evidence_dir / "certification-public-key.gpg"
    with public_key.open("wb") as output:
        run(["gpg", "--batch", "--export", fingerprint], cwd=args.checkout, env=env, stdout=output)
    if not public_key.stat().st_size:
        raise SystemExit("ephemeral certification public key export is empty")

    run(
        [
            "python3", "scripts/build-supralinux-proposed.py",
            "--plan", str(plan),
            "--artifact-root", str(args.artifact_root),
            "--output", str(repository),
            "--manifest", str(repository_manifest),
            "--signing-key", fingerprint,
            "--signed-certification",
        ],
        cwd=args.checkout,
        env=env,
    )

    repo_payload = json.loads(repository_manifest.read_text())
    signing = repo_payload.get("signing") or {}
    if not (
        repo_payload.get("state") == "PASS"
        and repo_payload.get("candidate_count") == 24
        and repo_payload.get("signed") is True
        and repo_payload.get("certification_mode") == "signed"
        and repo_payload.get("activation_eligible") is False
        and repo_payload.get("stable_publication_authorized") is False
        and repo_payload.get("package_attempt_consumed") is False
        and repo_payload.get("canonical_package_state_effect") == "none"
        and signing.get("fingerprint") == fingerprint
    ):
        raise SystemExit("signed proposed repository returned an invalid certification receipt")

    suite = plan_payload["suite"]
    release = repository / "dists" / suite / "Release"
    inrelease = repository / "dists" / suite / "InRelease"
    release_gpg = repository / "dists" / suite / "Release.gpg"
    packages = repository / "dists" / suite / "main" / "binary-amd64" / "Packages"
    sources = repository / "dists" / suite / "main" / "source" / "Sources"
    for path in (release, inrelease, release_gpg, packages, sources):
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"signed proposed repository output missing: {path}")

    expected = sealed["certification"]
    if sha256(packages) != expected["packages_sha256"]:
        raise SystemExit("signed proposed Packages digest differs from sealed content")
    if sha256(sources) != expected["sources_sha256"]:
        raise SystemExit("signed proposed Sources digest differs from sealed content")
    if sha256(release) != expected["release_sha256"]:
        raise SystemExit("signed proposed Release digest differs from sealed content")

    run(["gpgv", "--keyring", str(public_key), str(inrelease)], cwd=args.checkout)
    run(["gpgv", "--keyring", str(public_key), str(release_gpg), str(release)], cwd=args.checkout)
    extracted_release = args.work_dir / "release-from-inrelease"
    run(
        ["gpg", "--batch", "--yes", "--output", str(extracted_release), "--decrypt", str(inrelease)],
        cwd=args.checkout,
        env=env,
    )
    if sha256(extracted_release) != sha256(release):
        raise SystemExit("InRelease signed payload differs from Release")

    result = {
        "schema": 1,
        "state": "PASS",
        "kind": "supralinux-proposed-signing-certification",
        "source_commit": args.source_commit,
        "suite": suite,
        "candidate_count": 24,
        "frameworks_pass_nodes": 65,
        "sealed_content_source_commit": sealed["certification"]["source_commit"],
        "sealed_content_result_sha256": sealed["certification"]["result_sha256"],
        "plan_sha256": sha256(plan),
        "repository_manifest_sha256": sha256(repository_manifest),
        "packages_sha256": sha256(packages),
        "sources_sha256": sha256(sources),
        "release_sha256": sha256(release),
        "signing_fingerprint": fingerprint,
        "public_key_sha256": sha256(public_key),
        "inrelease_sha256": sha256(inrelease),
        "release_gpg_sha256": sha256(release_gpg),
        "signed": True,
        "signature_verification": "PASS",
        "builder_activation_eligible": False,
        "production_activation_eligible": False,
        "repository_active": False,
        "ephemeral_signing_key": True,
        "private_signing_key_retained": False,
        "stable_publication_authorized": False,
        "canonical_package_state_effect": "none",
        "package_attempt_consumed": False,
        "sbuild_invoked": False,
        "vm_created": False,
        "jit_invoked": False,
        "network_required": False,
    }
    (args.evidence_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        "SupraLINUX-proposed signing certification: PASS; "
        f"candidates={result['candidate_count']} fingerprint={fingerprint}"
    )


if __name__ == "__main__":
    main()
