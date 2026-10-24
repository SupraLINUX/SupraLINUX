#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import shutil
import stat
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPOSITORY = "SupraLINUX/SupraLINUX"
PR_NUMBER = 1
CAMPAIGN = "manifests/kde-plasma-package-build.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args, *, cwd=None, check=True):
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            check=check,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            sys.stderr.write(exc.stdout)
            if not exc.stdout.endswith("\n"):
                sys.stderr.write("\n")
        if exc.stderr:
            sys.stderr.write(exc.stderr)
            if not exc.stderr.endswith("\n"):
                sys.stderr.write("\n")
        raise


def gh_bytes(path: str) -> bytes:
    transient_codes = ("HTTP 429", "HTTP 502", "HTTP 503", "HTTP 504")
    proc = None
    for attempt in range(4):
        proc = subprocess.run(
            ["gh", "api", path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode == 0:
            return proc.stdout
        stderr = proc.stderr.decode(errors="replace")
        transient = any(code in stderr for code in transient_codes)
        if not transient or attempt == 3:
            if stderr:
                sys.stderr.write(stderr)
                if not stderr.endswith("\n"):
                    sys.stderr.write("\n")
            raise subprocess.CalledProcessError(
                proc.returncode,
                proc.args,
                output=proc.stdout,
                stderr=proc.stderr,
            )
        time.sleep(2 ** attempt)
    raise SystemExit("unreachable GitHub API retry state")


def exact_checkout(path: Path, commit: str) -> None:
    path.mkdir(parents=True)
    run(["git", "init", "-q", str(path)])
    run(["git", "-C", str(path), "remote", "add", "origin", f"https://github.com/{REPOSITORY}.git"])
    run(["git", "-C", str(path), "fetch", "-q", "--depth=1", "origin", commit])
    run(["git", "-C", str(path), "checkout", "-q", "--detach", "FETCH_HEAD"])
    resolved = run(["git", "-C", str(path), "rev-parse", "HEAD"]).stdout.strip()
    if resolved != commit:
        raise SystemExit(f"Exact checkout mismatch: expected {commit}, got {resolved}")
    dirty = run(
        ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=normal"]
    ).stdout
    if dirty:
        raise SystemExit("Exact checkout is not clean before evidence closure.")


def find_host_evidence(root: Path, package_run_id: int, manifest_sha256: str) -> Path:
    matches = []
    for manifest in sorted(root.glob("*/evidence-sha256.txt")):
        try:
            if sha256(manifest) != manifest_sha256:
                continue
            host_result = json.loads((manifest.parent / "host-result.json").read_text())
            if host_result.get("workflow_run_id") != str(package_run_id):
                continue
            matches.append(manifest.parent)
        except (OSError, json.JSONDecodeError):
            continue
    if len(matches) != 1:
        raise SystemExit(
            f"Expected one sealed host evidence directory, found {len(matches)}"
        )
    host_dir = matches[0]
    run(["sha256sum", "--check", "--quiet", "evidence-sha256.txt"], cwd=host_dir)
    return host_dir


def changed_files(checkout: Path):
    deleted = run(
        ["git", "-C", str(checkout), "diff", "--name-only", "--diff-filter=D"]
    ).stdout.splitlines()
    if deleted:
        raise SystemExit(
            f"Evidence closure unexpectedly deleted tracked files: {deleted!r}"
        )
    modified = run(
        ["git", "-C", str(checkout), "diff", "--name-only", "--diff-filter=ACMRTUXB"]
    ).stdout.splitlines()
    untracked = run(
        ["git", "-C", str(checkout), "ls-files", "--others", "--exclude-standard"]
    ).stdout.splitlines()
    return sorted(set(modified + untracked))


def allowed_change(path: str, node: str) -> bool:
    if path in {
        "docs/status/current.md",
        "manifests/kde-plasma-package-build.json",
        "manifests/kde-plasma.json",
        "manifests/kde-plasma-level0.json",
        "manifests/kde-plasma-supplementary-providers.json",
        f"manifests/evidence/plasma/{node}-artifact-plan.json",
    }:
        return True
    escaped = re.escape(node)
    return bool(
        re.fullmatch(
            rf"manifests/evidence/package-revalidation/{escaped}-preflight[0-9]+/.+",
            path,
        )
        or re.fullmatch(
            rf"manifests/evidence/plasma/{escaped}-attempt[0-9]+/.+",
            path,
        )
    )


def export_update(
    checkout: Path,
    node: str,
    output_dir: Path,
    manifest_path: Path,
):
    files = changed_files(checkout)
    if not files:
        raise SystemExit("Evidence closure produced no canonical changes.")
    unexpected = [path for path in files if not allowed_change(path, node)]
    if unexpected:
        raise SystemExit(
            f"Evidence closure changed unexpected paths: {unexpected!r}"
        )
    required = {
        "docs/status/current.md",
        "manifests/kde-plasma-package-build.json",
    }
    if not required.issubset(files):
        raise SystemExit(
            "Evidence closure is missing expected canonical changes: "
            f"{sorted(required - set(files))!r}"
        )
    output_dir.mkdir(parents=True)
    entries = []
    for relative in files:
        source = checkout / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(
                f"Canonical update path is not a regular file: {relative}"
            )
        target = output_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        entries.append(
            {
                "path": relative,
                "sha256": sha256(source),
                "mode": format(stat.S_IMODE(source.stat().st_mode), "04o"),
            }
        )
    manifest_path.write_text(
        json.dumps({"schema": 1, "files": entries}, indent=2) + "\n"
    )
    return entries



def publication_commit_message(closed_campaign, node, closure_kind):
    record = closed_campaign["nodes"][node]
    if closure_kind == "preflight":
        if closed_campaign.get("execution_mode") != "build":
            raise SystemExit("Canonical preflight publish did not authorize package build.")
        if record.get("state") != "build-pending":
            raise SystemExit("Canonical preflight publish changed package state unexpectedly.")
        certifications = closed_campaign.get("package_input_certifications", [])
        if not certifications or not isinstance(certifications[-1], dict):
            raise SystemExit("Canonical preflight publish lacks an input certification.")
        if certifications[-1].get("applicable") is False:
            raise SystemExit("Canonical preflight publish certification is not applicable.")
        return f"evidence: close {node} input preflight"
    if closure_kind == "package-attempt-pass":
        attempts = record.get("attempts", [])
        if not attempts or attempts[-1].get("state") != "PASS":
            raise SystemExit("Canonical publish lacks a final PASS Attempt.")
        return f"evidence: close {node} Attempt {attempts[-1]['attempt']}"
    raise SystemExit(f"Unsupported canonical publication closure kind: {closure_kind}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Close or replay authoritative package evidence without "
            "host shell payloads."
        )
    )
    parser.add_argument("--mode", choices=["check", "close", "publish-check", "publish"], required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--control-run-id", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--package-run-id", type=int, required=True)
    parser.add_argument("--package-job-id", type=int, required=True)
    parser.add_argument("--package-artifact-id", type=int, required=True)
    parser.add_argument("--package-artifact-sha256", required=True)
    parser.add_argument("--host-manifest-sha256", required=True)
    parser.add_argument("--host-evidence-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        raise SystemExit("Invalid current source commit.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]{0,63}", args.node):
        raise SystemExit("Invalid evidence node.")
    if not re.fullmatch(r"[0-9a-f]{64}", args.package_artifact_sha256):
        raise SystemExit("Invalid package artifact SHA-256.")
    if not re.fullmatch(r"[0-9a-f]{64}", args.host_manifest_sha256):
        raise SystemExit("Invalid host manifest SHA-256.")
    if (
        args.package_run_id <= 0
        or args.package_job_id <= 0
        or args.package_artifact_id <= 0
    ):
        raise SystemExit("Invalid package evidence identifiers.")

    run(["gh", "auth", "status", "--hostname", "github.com"])
    pr_bytes = gh_bytes(f"repos/{REPOSITORY}/pulls/{PR_NUMBER}")
    pr = json.loads(pr_bytes)
    if not (
        pr.get("state") == "open"
        and pr.get("head", {}).get("sha") == args.source_commit
        and pr.get("head", {}).get("repo", {}).get("full_name") == REPOSITORY
    ):
        raise SystemExit(
            "Current PR identity/head does not match the closure request."
        )

    artifact_meta_bytes = gh_bytes(
        f"repos/{REPOSITORY}/actions/artifacts/{args.package_artifact_id}"
    )
    job_bytes = gh_bytes(
        f"repos/{REPOSITORY}/actions/jobs/{args.package_job_id}"
    )
    artifact = json.loads(artifact_meta_bytes)
    job = json.loads(job_bytes)
    if artifact.get("id") != args.package_artifact_id:
        raise SystemExit("Artifact ID mismatch.")
    if artifact.get("digest") != "sha256:" + args.package_artifact_sha256:
        raise SystemExit("Artifact metadata digest mismatch.")
    if artifact.get("workflow_run", {}).get("id") != args.package_run_id:
        raise SystemExit("Artifact workflow run mismatch.")
    if (
        job.get("id") != args.package_job_id
        or job.get("run_id") != args.package_run_id
    ):
        raise SystemExit("Workflow job identity mismatch.")
    if job.get("status") != "completed":
        raise SystemExit("Package workflow job is not complete.")
    package_head = job.get("head_sha")
    if (
        not isinstance(package_head, str)
        or not re.fullmatch(r"[0-9a-f]{40}", package_head)
    ):
        raise SystemExit("Package workflow job has no valid head SHA.")
    if artifact.get("workflow_run", {}).get("head_sha") != package_head:
        raise SystemExit("Artifact and workflow job head SHAs differ.")

    args.work_root.mkdir(parents=True)
    current_checkout = args.work_root / "current"
    replay_checkout = args.work_root / "replay"
    exact_checkout(current_checkout, args.source_commit)
    exact_checkout(replay_checkout, package_head)

    artifact_zip = args.work_root / "package-artifact.zip"
    artifact_zip.write_bytes(
        gh_bytes(
            f"repos/{REPOSITORY}/actions/artifacts/"
            f"{args.package_artifact_id}/zip"
        )
    )
    if sha256(artifact_zip) != args.package_artifact_sha256:
        raise SystemExit("Downloaded package artifact digest mismatch.")
    artifact_meta = args.work_root / "artifact-meta.json"
    artifact_meta.write_bytes(artifact_meta_bytes)
    job_json = args.work_root / "workflow-job.json"
    job_json.write_bytes(job_bytes)

    with zipfile.ZipFile(artifact_zip) as archive:
        result = json.loads(archive.read("result.json"))
    if result.get("node") != args.node:
        raise SystemExit("Package result node mismatch.")
    if result.get("source_commit") != package_head:
        raise SystemExit("Package result source commit mismatch.")
    if result.get("workflow_run_id") != str(args.package_run_id):
        raise SystemExit("Package result workflow run mismatch.")

    if result.get("state") != "PASS":
        raw = (
            args.artifact_root
            / "raw"
            / args.node
            / str(args.package_run_id)
        )
        raw.mkdir(parents=True, exist_ok=True)
        retained = raw / f"{args.package_artifact_sha256}.zip"
        if (
            retained.exists()
            and sha256(retained) != args.package_artifact_sha256
        ):
            raise SystemExit("Conflicting retained raw package artifact.")
        if not retained.exists():
            shutil.copyfile(artifact_zip, retained)
        args.output_dir.mkdir(parents=True)
        receipt = {
            "schema": 1,
            "state": "DIAGNOSIS_REQUIRED",
            "node": args.node,
            "source_commit": package_head,
            "workflow_run_id": args.package_run_id,
            "workflow_job_id": args.package_job_id,
            "artifact_id": args.package_artifact_id,
            "artifact_sha256": args.package_artifact_sha256,
            "original_state": result.get("state"),
            "stage": result.get("stage"),
            "package_attempt_consumed": result.get(
                "package_attempt_consumed"
            ),
            "retained_raw_artifact": str(retained),
            "canonical_update_created": False,
        }
        (args.output_dir / "close-evidence-result.json").write_text(
            json.dumps(receipt, indent=2) + "\n"
        )
        raise SystemExit(3)

    host_dir = find_host_evidence(
        args.host_evidence_root,
        args.package_run_id,
        args.host_manifest_sha256,
    )
    host_result = json.loads(
        (host_dir / "host-result.json").read_text()
    )
    if host_result.get("exit_code") != 0:
        raise SystemExit(
            "Successful package artifact is not paired with a "
            "successful sealed host result."
        )

    args.artifact_root.mkdir(parents=True, exist_ok=True)
    logical_artifacts = replay_checkout / ".artifacts"
    if logical_artifacts.exists() or logical_artifacts.is_symlink():
        raise SystemExit(
            "Replay checkout unexpectedly contains .artifacts."
        )
    logical_artifacts.symlink_to(
        args.artifact_root,
        target_is_directory=True,
    )
    try:
        if result.get("package_attempt_consumed") is False:
            close_cmd = [
                "python3",
                "scripts/close-package-revalidation-evidence.py",
                args.node,
                "--campaign",
                CAMPAIGN,
                "--zip",
                str(artifact_zip),
                "--artifact-meta",
                str(artifact_meta),
                "--job-json",
                str(job_json),
                "--host-dir",
                str(host_dir),
            ]
            closure_kind = "preflight"
        elif result.get("package_attempt_consumed") is True:
            close_cmd = [
                "python3",
                "scripts/close-plasma-package-evidence.py",
                args.node,
                "--zip",
                str(artifact_zip),
                "--artifact-meta",
                str(artifact_meta),
                "--workflow-job-meta",
                str(job_json),
                "--host-dir",
                str(host_dir),
                "--job-id",
                str(args.package_job_id),
                "--recover-hidden-files",
            ]
            closure_kind = "package-attempt-pass"
        else:
            raise SystemExit(
                "Package result lacks an explicit "
                "package_attempt_consumed boolean."
            )
        run(close_cmd, cwd=replay_checkout)
    finally:
        if logical_artifacts.is_symlink():
            logical_artifacts.unlink()

    run(
        ["python3", "scripts/render-project-status.py"],
        cwd=replay_checkout,
    )
    run(
        ["python3", "scripts/check-source-syntax.py"],
        cwd=replay_checkout,
    )
    run(
        ["python3", "scripts/validate_plasma_package_build.py"],
        cwd=replay_checkout,
    )
    run(
        ["python3", "scripts/render-project-status.py", "--check"],
        cwd=replay_checkout,
    )

    export_dir = args.output_dir / "canonical-update"
    update_manifest = (
        args.output_dir / "canonical-update-manifest.json"
    )
    entries = export_update(
        replay_checkout,
        args.node,
        export_dir,
        update_manifest,
    )

    retained = list(
        args.artifact_root.rglob(
            f"{args.package_artifact_sha256}.zip"
        )
    )
    if (
        len(retained) != 1
        or sha256(retained[0]) != args.package_artifact_sha256
    ):
        raise SystemExit(
            "Offline retained artifact could not be identified uniquely."
        )

    if args.mode == "check":
        for entry in entries:
            current = current_checkout / entry["path"]
            if (
                not current.is_file()
                or sha256(current) != entry["sha256"]
            ):
                raise SystemExit(
                    "Closure replay differs from current canonical file: "
                    f"{entry['path']}"
                )
        canonical_update_created = False
        shutil.rmtree(export_dir)
    else:
        run(
            [
                "git",
                "-C",
                str(current_checkout),
                "fetch",
                "-q",
                "--depth=1",
                "origin",
                package_head,
            ]
        )
        paths = [entry["path"] for entry in entries]
        conflicts = run(
            [
                "git",
                "-C",
                str(current_checkout),
                "diff",
                "--name-only",
                package_head,
                args.source_commit,
                "--",
                *paths,
            ]
        ).stdout.splitlines()
        if conflicts:
            raise SystemExit(
                "Canonical paths changed after package execution: "
                f"{conflicts!r}"
            )
        canonical_update_created = True

    canonical_commit = None
    published = False
    publish_dry_run = False
    if args.mode in {"publish-check", "publish"}:
        publish_checkout = args.work_root / "publish"
        exact_checkout(publish_checkout, args.source_commit)
        for entry in entries:
            source = export_dir / entry["path"]
            target = publish_checkout / entry["path"]
            if (
                not source.is_file()
                or source.is_symlink()
                or sha256(source) != entry["sha256"]
            ):
                raise SystemExit(
                    "Canonical publish source failed hash admission: "
                    f"{entry['path']}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if sha256(target) != entry["sha256"]:
                raise SystemExit(
                    "Canonical publish copy changed bytes: "
                    f"{entry['path']}"
                )

        paths = [entry["path"] for entry in entries]
        actual_changes = changed_files(publish_checkout)
        if actual_changes != sorted(paths):
            raise SystemExit(
                "Canonical publish change set differs from closure manifest: "
                f"{actual_changes!r}"
            )

        for command in [
            ["python3", "scripts/check-source-syntax.py"],
            ["python3", "scripts/validate_plasma_package_build.py"],
            ["python3", "scripts/render-project-status.py", "--check"],
            ["python3", "scripts/validate_repository.py"],
        ]:
            run(command, cwd=publish_checkout)

        run(["git", "-C", str(publish_checkout), "add", "--", *paths])
        staged = run(
            ["git", "-C", str(publish_checkout), "diff", "--cached", "--name-only"]
        ).stdout.splitlines()
        if sorted(staged) != sorted(paths):
            raise SystemExit(
                "Canonical publish staged set differs from closure manifest."
            )
        run(["git", "-C", str(publish_checkout), "diff", "--cached", "--check"])

        author = pr.get("user", {})
        author_login = author.get("login")
        author_id = author.get("id")
        if (
            not isinstance(author_login, str)
            or not re.fullmatch(r"[A-Za-z0-9-]+", author_login)
            or not isinstance(author_id, int)
            or author_id <= 0
        ):
            raise SystemExit("Could not resolve a safe PR author identity.")
        run(
            [
                "git", "-C", str(publish_checkout), "config",
                "user.name", author_login,
            ]
        )
        run(
            [
                "git", "-C", str(publish_checkout), "config",
                "user.email",
                f"{author_id}+{author_login}@users.noreply.github.com",
            ]
        )
        closed_campaign = json.loads(
            (publish_checkout / CAMPAIGN).read_text()
        )
        commit_message = publication_commit_message(
            closed_campaign, args.node, closure_kind
        )
        run(
            [
                "git", "-C", str(publish_checkout), "commit", "-q",
                "-m", commit_message,
            ]
        )
        canonical_commit = run(
            ["git", "-C", str(publish_checkout), "rev-parse", "HEAD"]
        ).stdout.strip()
        parent = run(
            ["git", "-C", str(publish_checkout), "rev-parse", "HEAD^"]
        ).stdout.strip()
        if parent != args.source_commit:
            raise SystemExit("Canonical publish commit parent changed unexpectedly.")

        branch = pr.get("head", {}).get("ref")
        if (
            not isinstance(branch, str)
            or not re.fullmatch(r"[A-Za-z0-9._/-]{1,200}", branch)
            or branch.startswith("/")
            or ".." in branch.split("/")
        ):
            raise SystemExit("Unsafe PR head branch for canonical publication.")

        current_pr = json.loads(
            gh_bytes(f"repos/{REPOSITORY}/pulls/{PR_NUMBER}")
        )
        if current_pr.get("head", {}).get("sha") != args.source_commit:
            raise SystemExit("PR head changed before canonical publication.")

        push = [
            "git", "-C", str(publish_checkout),
            "-c", "credential.helper=!gh auth git-credential",
            "push",
            f"--force-with-lease=refs/heads/{branch}:{args.source_commit}",
        ]
        if args.mode == "publish-check":
            push.append("--dry-run")
            publish_dry_run = True
        push.extend(["origin", f"HEAD:refs/heads/{branch}"])
        run(push)

        if args.mode == "publish":
            remote_ref = f"refs/heads/{branch}"
            observed_remote = None
            for attempt in range(4):
                remote = run(
                    [
                        "git", "-C", str(publish_checkout),
                        "-c", "credential.helper=!gh auth git-credential",
                        "ls-remote", "--heads", "origin", remote_ref,
                    ],
                    check=False,
                )
                lines = [
                    line.split()
                    for line in remote.stdout.splitlines()
                    if line.strip()
                ]
                if (
                    remote.returncode == 0
                    and len(lines) == 1
                    and len(lines[0]) == 2
                    and lines[0][1] == remote_ref
                ):
                    observed_remote = lines[0][0]
                    if observed_remote == canonical_commit:
                        break
                if attempt != 3:
                    time.sleep(2 ** attempt)
            if observed_remote != canonical_commit:
                raise SystemExit(
                    "Published canonical commit is not the exact remote branch ref."
                )
            published = True

    receipt = {
        "schema": 1,
        "state": "PASS",
        "mode": args.mode,
        "closure_kind": closure_kind,
        "node": args.node,
        "control_source_commit": args.source_commit,
        "package_source_commit": package_head,
        "workflow_run_id": args.package_run_id,
        "workflow_job_id": args.package_job_id,
        "artifact_id": args.package_artifact_id,
        "artifact_sha256": args.package_artifact_sha256,
        "host_evidence_dir": str(host_dir),
        "host_evidence_manifest_sha256": (
            args.host_manifest_sha256
        ),
        "package_attempt_consumed": result.get(
            "package_attempt_consumed"
        ),
        "canonical_update_created": canonical_update_created,
        "canonical_update_file_count": len(entries),
        "canonical_update_manifest_sha256": sha256(
            update_manifest
        ),
        "canonical_commit": canonical_commit,
        "publish_dry_run": publish_dry_run,
        "published": published,
        "offline_retained_artifact": str(retained[0]),
        "offline_restore_verified": True,
        "requires_github_for_restore": False,
    }
    (args.output_dir / "close-evidence-result.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
