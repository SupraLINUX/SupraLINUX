#!/usr/bin/env python3
"""Restore exact retained Plasma artifacts required by SupraLINUX-proposed."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

API_VERSION = "2026-03-10"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_digest(digest: str) -> None:
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
    ):
        raise SystemExit(f"invalid artifact SHA-256: {digest!r}")


def logical_parts(archive_root: str) -> tuple[str, ...]:
    path = Path(archive_root)
    parts = path.parts
    if (
        path.is_absolute()
        or len(parts) < 2
        or parts[0] != ".artifacts"
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise SystemExit(f"invalid retained artifact root: {archive_root!r}")
    return parts[1:]


def real_root(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if path.is_symlink() or not resolved.is_dir():
        raise SystemExit(f"artifact root must be a real directory: {path}")
    return resolved


def ensure_child_directory(root: Path, parts: tuple[str, ...]) -> Path:
    current = real_root(root)
    for part in parts:
        candidate = current / part
        if candidate.is_symlink():
            raise SystemExit(f"refusing symlink in retained artifact path: {candidate}")
        if candidate.exists():
            if not candidate.is_dir():
                raise SystemExit(f"retained artifact path is not a directory: {candidate}")
        else:
            candidate.mkdir(mode=0o700)
        resolved = candidate.resolve(strict=True)
        if resolved != candidate:
            raise SystemExit(f"retained artifact path traverses a symlink: {candidate}")
        current = candidate
    return current


def artifact_target(root: Path, archive_root: str, digest: str) -> Path:
    validate_digest(digest)
    archive = ensure_child_directory(root, logical_parts(archive_root))
    sha_dir = ensure_child_directory(archive, ("sha256",))
    target = sha_dir / f"{digest}.zip"
    if target.is_symlink():
        raise SystemExit(f"refusing retained artifact symlink: {target}")
    return target


def has_symlink_between(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def find_legacy_artifact(
    roots: list[Path],
    archive_root: str,
    digest: str,
) -> Path | None:
    validate_digest(digest)
    relative = logical_parts(archive_root)
    seen: set[Path] = set()
    for supplied_root in roots:
        try:
            root = real_root(supplied_root)
        except (FileNotFoundError, OSError, SystemExit):
            continue
        exact = root.joinpath(*relative) / "sha256" / f"{digest}.zip"
        candidates = [exact]
        try:
            candidates.extend(root.rglob(f"{digest}.zip"))
        except OSError:
            pass
        for candidate in candidates:
            try:
                resolved = candidate.resolve(strict=True)
            except (FileNotFoundError, OSError):
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            if (
                has_symlink_between(root, candidate)
                or not candidate.is_file()
                or candidate.is_symlink()
            ):
                continue
            try:
                if sha256(candidate) == digest:
                    return candidate
            except OSError:
                continue
    return None


def find_legacy_index(
    roots: list[Path],
    archive_root: str,
    expected_digest: str,
) -> Path | None:
    validate_digest(expected_digest)
    relative = logical_parts(archive_root)
    for supplied_root in roots:
        try:
            root = real_root(supplied_root)
        except (FileNotFoundError, OSError, SystemExit):
            continue
        candidate = root.joinpath(*relative) / "index.json"
        try:
            candidate.resolve(strict=True)
        except (FileNotFoundError, OSError):
            continue
        if (
            has_symlink_between(root, candidate)
            or not candidate.is_file()
            or candidate.is_symlink()
        ):
            continue
        try:
            if sha256(candidate) == expected_digest:
                return candidate
        except OSError:
            continue
    return None


def atomic_install(source: Path, target: Path, expected_digest: str) -> None:
    validate_digest(expected_digest)
    if target.exists():
        if target.is_symlink() or not target.is_file():
            raise SystemExit(f"conflicting retained artifact target: {target}")
        if sha256(target) != expected_digest:
            raise SystemExit(f"retained artifact digest drift: {target}")
        return
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    os.close(fd)
    temporary = Path(temp_name)
    try:
        with source.open("rb") as incoming, temporary.open("wb") as output:
            shutil.copyfileobj(incoming, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        if sha256(temporary) != expected_digest:
            raise SystemExit(f"artifact copy digest mismatch for {target}")
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_bytes(payload: bytes, target: Path, expected_digest: str) -> None:
    validate_digest(expected_digest)
    if hashlib.sha256(payload).hexdigest() != expected_digest:
        raise SystemExit(f"generated retained index digest mismatch for {target}")
    if target.exists():
        if target.is_symlink() or not target.is_file():
            raise SystemExit(f"conflicting retained index target: {target}")
        if sha256(target) != expected_digest:
            raise SystemExit(f"retained index digest drift: {target}")
        return
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    os.close(fd)
    temporary = Path(temp_name)
    try:
        with temporary.open("wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and urlparse(req.full_url).hostname != urlparse(newurl).hostname:
            redirected.remove_header("Authorization")
        return redirected


def github_token() -> str:
    proc = subprocess.run(
        ["gh", "auth", "token"],
        check=True,
        capture_output=True,
        text=True,
    )
    token = proc.stdout.strip()
    if not token:
        raise SystemExit("GitHub host authentication returned an empty token")
    return token


def download_artifact(
    repository: str,
    artifact_id: int,
    destination: Path,
    token: str,
) -> bool:
    url = f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    opener = urllib.request.build_opener(SafeRedirectHandler())
    last_error: Exception | None = None
    for attempt in range(4):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "SupraLINUX-proposed-artifact-recovery",
            },
        )
        try:
            with opener.open(request, timeout=180) as response, destination.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            return True
        except urllib.error.HTTPError as exc:
            destination.unlink(missing_ok=True)
            if exc.code in {404, 410}:
                return False
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 3:
                break
        except (urllib.error.URLError, TimeoutError) as exc:
            destination.unlink(missing_ok=True)
            last_error = exc
            if attempt == 3:
                break
        time.sleep(2 ** attempt)
    raise SystemExit(f"artifact {artifact_id} download failed: {last_error}")


def verified_index_bytes(
    checkout: Path,
    node: str,
    candidate: dict,
    record: dict,
    artifact: Path,
) -> tuple[bytes | None, str]:
    local = (record.get("evidence") or {}).get("local_retention") or {}
    plan_rel = Path(local.get("plan_path", ""))
    if (
        plan_rel.is_absolute()
        or not plan_rel.parts
        or any(part in {"", ".", ".."} for part in plan_rel.parts)
    ):
        raise SystemExit(f"{node}: invalid historical artifact plan path")
    plan_path = checkout / plan_rel
    if not plan_path.is_file() or plan_path.is_symlink():
        raise SystemExit(f"{node}: historical artifact plan is missing")
    expected_plan_sha = local.get("plan_sha256")
    validate_digest(expected_plan_sha)
    if sha256(plan_path) != expected_plan_sha:
        raise SystemExit(f"{node}: historical artifact plan digest drift")

    plan = json.loads(plan_path.read_text())
    items = plan.get("items", [])
    if len(items) != 1:
        raise SystemExit(f"{node}: historical artifact plan is not single-node")
    item = items[0]
    if not (
        item.get("node") == node
        and item.get("artifact_sha256") == candidate["artifact_sha256"]
        and item.get("package_version") == candidate["version"]
        and item.get("artifact_id") == candidate.get("artifact_id")
    ):
        raise SystemExit(f"{node}: proposed candidate differs from historical artifact plan")

    expected_index_sha = local.get("archive_index_sha256")
    validate_digest(expected_index_sha)
    with tempfile.TemporaryDirectory(prefix=f"supralinux-proposed-recovery-{node}-") as directory:
        archive = Path(directory) / "archive"
        sha_dir = archive / "sha256"
        sha_dir.mkdir(parents=True)
        staged = sha_dir / f"{candidate['artifact_sha256']}.zip"
        shutil.copyfile(artifact, staged)
        proc = subprocess.run(
            [
                "python3",
                "scripts/retain-package-artifacts.py",
                "--plan", str(plan_path),
                "--archive", str(archive),
                "--allow-legacy-source-gaps",
            ],
            cwd=checkout,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if proc.returncode != 0:
            detail = proc.stdout[-4000:]
            raise SystemExit(
                f"{node}: retained artifact failed historical identity verification:\n{detail}"
            )
        index = archive / "index.json"
        if not index.is_file() or index.is_symlink():
            raise SystemExit(f"{node}: retained verifier did not produce an index")
        actual_index_sha = sha256(index)
        if actual_index_sha != expected_index_sha:
            return None, actual_index_sha
        return index.read_bytes(), actual_index_sha


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--repository", default="SupraLINUX/SupraLINUX")
    parser.add_argument(
        "--legacy-search-root",
        action="append",
        type=Path,
        default=[],
        help="bounded historical archive root searched only for exact retained digests",
    )
    args = parser.parse_args()

    checkout = real_root(args.checkout)
    artifact_root = real_root(args.artifact_root)
    args.result.parent.mkdir(parents=True, exist_ok=True)

    plan_proc = subprocess.run(
        ["python3", "scripts/plan-supralinux-proposed.py"],
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    )
    plan = json.loads(plan_proc.stdout)
    if plan.get("state") != "PASS" or plan.get("candidate_count") != len(plan.get("candidates", [])):
        raise SystemExit("invalid SupraLINUX-proposed candidate plan")
    campaign = json.loads((checkout / "manifests/kde-plasma-package-build.json").read_text())

    rows = []
    reused = restored_github = restored_legacy = 0
    index_reused = index_restored_legacy = index_rebuilt = 0
    unresolved = []
    token: str | None = None
    try:
        for candidate in plan["candidates"]:
            node = candidate["node"]
            digest = candidate["artifact_sha256"]
            validate_digest(digest)
            record = campaign["nodes"].get(node)
            if not isinstance(record, dict) or record.get("state") != "PASS":
                raise SystemExit(f"{node}: current campaign record is not PASS")
            local = (record.get("evidence") or {}).get("local_retention") or {}
            archive_root = local.get("archive_root")
            if candidate.get("retention", {}).get("archive_root") != archive_root:
                raise SystemExit(f"{node}: proposed retention root differs from campaign evidence")
            archive_dir = ensure_child_directory(artifact_root, logical_parts(archive_root))
            target = artifact_target(artifact_root, archive_root, digest)

            action = None
            artifact = None
            if target.exists():
                if not target.is_file() or target.is_symlink() or sha256(target) != digest:
                    raise SystemExit(f"{node}: persistent retained artifact has digest drift")
                artifact = target
                action = "reused"
                reused += 1
            else:
                legacy = find_legacy_artifact(args.legacy_search_root, archive_root, digest)
                if legacy is not None:
                    artifact = legacy
                    action = "restored-legacy"
                elif isinstance(candidate.get("artifact_id"), int):
                    if token is None:
                        token = github_token()
                    fd, temp_name = tempfile.mkstemp(
                        prefix=f"{candidate['artifact_id']}.", suffix=".zip.tmp", dir=target.parent
                    )
                    os.close(fd)
                    temporary = Path(temp_name)
                    try:
                        available = download_artifact(
                            args.repository,
                            candidate["artifact_id"],
                            temporary,
                            token,
                        )
                        if not available:
                            unresolved.append(
                                {
                                    "node": node,
                                    "reason": "github-artifact-unavailable",
                                    "artifact_id": candidate["artifact_id"],
                                    "artifact_sha256": digest,
                                }
                            )
                            rows.append(
                                {
                                    "node": node,
                                    "state": "BLOCKED",
                                    "artifact": "missing",
                                    "index": "not-checked",
                                }
                            )
                            continue
                        if sha256(temporary) != digest:
                            raise SystemExit(f"{node}: downloaded artifact digest mismatch")
                        artifact = temporary
                        action = "restored-github"
                        index_bytes, generated_index_sha = verified_index_bytes(
                            checkout, node, candidate, record, artifact
                        )
                        atomic_install(artifact, target, digest)
                        artifact = target
                        restored_github += 1
                    finally:
                        temporary.unlink(missing_ok=True)
                else:
                    unresolved.append(
                        {
                            "node": node,
                            "reason": "offline-retained-artifact-not-found",
                            "artifact_id": None,
                            "artifact_sha256": digest,
                        }
                    )
                    rows.append(
                        {
                            "node": node,
                            "state": "BLOCKED",
                            "artifact": "missing",
                            "index": "not-checked",
                        }
                    )
                    continue

            if action != "restored-github":
                index_bytes, generated_index_sha = verified_index_bytes(
                    checkout, node, candidate, record, artifact
                )
                if artifact != target:
                    atomic_install(artifact, target, digest)
                    artifact = target
                    restored_legacy += 1

            expected_index_sha = local.get("archive_index_sha256")
            validate_digest(expected_index_sha)
            index_path = archive_dir / "index.json"
            index_state = None
            if index_path.exists():
                if index_path.is_symlink() or not index_path.is_file():
                    raise SystemExit(f"{node}: persistent retained index is not a regular file")
                if sha256(index_path) != expected_index_sha:
                    raise SystemExit(f"{node}: persistent retained index digest drift")
                index_state = "reused"
                index_reused += 1
            else:
                legacy_index = find_legacy_index(
                    args.legacy_search_root,
                    archive_root,
                    expected_index_sha,
                )
                if legacy_index is not None:
                    atomic_install(legacy_index, index_path, expected_index_sha)
                    index_state = "restored-legacy"
                    index_restored_legacy += 1
                elif index_bytes is not None:
                    atomic_write_bytes(index_bytes, index_path, expected_index_sha)
                    index_state = "rebuilt-exact"
                    index_rebuilt += 1
                else:
                    index_state = "unresolved"
                    unresolved.append(
                        {
                            "node": node,
                            "reason": "historical-index-digest-not-reproducible",
                            "expected_index_sha256": expected_index_sha,
                            "generated_index_sha256": generated_index_sha,
                        }
                    )

            rows.append(
                {
                    "node": node,
                    "state": "PASS" if index_state != "unresolved" else "BLOCKED",
                    "artifact": action,
                    "artifact_sha256": digest,
                    "index": index_state,
                    "archive_root": archive_root,
                }
            )
    finally:
        token = None

    state = "PASS" if not unresolved else "BLOCKED"
    result = {
        "schema": 1,
        "state": state,
        "kind": "supralinux-proposed-retained-artifact-recovery",
        "candidate_count": plan["candidate_count"],
        "reused": reused,
        "restored_from_github": restored_github,
        "restored_from_legacy": restored_legacy,
        "archive_indices_reused": index_reused,
        "archive_indices_restored_from_legacy": index_restored_legacy,
        "archive_indices_rebuilt_exactly": index_rebuilt,
        "unresolved_count": len(unresolved),
        "unresolved": unresolved,
        "rows": rows,
        "artifact_root": str(artifact_root),
        "network_required_for_repair": restored_github > 0,
        "package_attempt_consumed": False,
        "sbuild_invoked": False,
        "vm_created": False,
        "jit_invoked": False,
        "canonical_package_state_effect": "none",
        "stable_publication_authorized": False,
    }
    args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
