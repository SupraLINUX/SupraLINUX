#!/usr/bin/env python3
"""Restore the exact retained Frameworks 6.30 artifact archive from GitHub Actions."""

import argparse
import hashlib
import json
import os
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


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and urlparse(req.full_url).hostname != urlparse(newurl).hostname:
            redirected.remove_header("Authorization")
        return redirected


def github_token() -> str:
    proc = subprocess.run(["gh", "auth", "token"], check=True, capture_output=True, text=True)
    token = proc.stdout.strip()
    if not token:
        raise SystemExit("GitHub host authentication returned an empty token")
    return token


def download_artifact(repository: str, artifact_id: int, destination: Path, token: str) -> None:
    url = f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    opener = urllib.request.build_opener(SafeRedirectHandler())
    last_error = None
    for attempt in range(4):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "SupraLINUX-frameworks-artifact-recovery",
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
            return
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 3:
                break
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 3:
                break
        destination.unlink(missing_ok=True)
        time.sleep(2 ** attempt)
    raise SystemExit(f"artifact {artifact_id} download failed: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--repository", default="SupraLINUX/SupraLINUX")
    args = parser.parse_args()

    checkout = args.checkout.resolve(strict=True)
    archive = args.archive.resolve(strict=True)
    if archive.is_symlink() or not archive.is_dir():
        raise SystemExit("retained archive root must be a real directory")
    args.result.parent.mkdir(parents=True, exist_ok=True)

    retained = json.loads((checkout / "manifests/retained-package-artifacts.json").read_text())
    if retained.get("archive_root") != ".artifacts/frameworks-6.30":
        raise SystemExit("unexpected logical Frameworks archive root")
    if retained.get("artifact_count") != 65:
        raise SystemExit("unexpected retained Frameworks artifact count")

    plan_proc = subprocess.run(
        ["python3", "scripts/plan-frameworks-milestone.py"],
        cwd=checkout, check=True, capture_output=True, text=True,
    )
    plan = json.loads(plan_proc.stdout)
    if plan.get("artifact_count") != retained["artifact_count"]:
        raise SystemExit("Frameworks recovery plan count does not match retained manifest")

    plan_path = args.result.parent / "frameworks-recovery-plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    sha_dir = archive / "sha256"
    sha_dir.mkdir(mode=0o700, exist_ok=True)

    token = github_token()
    downloaded = 0
    reused = 0
    try:
        for item in plan["items"]:
            digest = item["artifact_sha256"]
            artifact_id = item["artifact_id"]
            target = sha_dir / f"{digest}.zip"
            if target.exists():
                if target.is_symlink() or not target.is_file() or sha256(target) != digest:
                    raise SystemExit(f"{item['node']}: conflicting retained artifact bytes")
                reused += 1
                continue
            fd, temp_name = tempfile.mkstemp(prefix=f"{artifact_id}.", suffix=".zip.tmp", dir=sha_dir)
            os.close(fd)
            temporary = Path(temp_name)
            try:
                download_artifact(args.repository, artifact_id, temporary, token)
                actual = sha256(temporary)
                if actual != digest:
                    raise SystemExit(
                        f"{item['node']}: downloaded artifact digest mismatch "
                        f"expected={digest} actual={actual}"
                    )
                os.chmod(temporary, 0o600)
                os.replace(temporary, target)
                downloaded += 1
            finally:
                temporary.unlink(missing_ok=True)
    finally:
        token = ""

    subprocess.run(
        [
            "python3", "scripts/retain-package-artifacts.py",
            "--plan", str(plan_path),
            "--archive", str(archive),
            "--allow-legacy-source-gaps",
        ],
        cwd=checkout, check=True,
    )

    index = archive / retained["archive_index"]
    if index.is_symlink() or not index.is_file():
        raise SystemExit("recovered Frameworks archive index is missing")
    actual_index_sha = sha256(index)
    expected_index_sha = retained["archive_index_sha256"]
    if actual_index_sha != expected_index_sha:
        raise SystemExit(
            "recovered Frameworks archive index digest mismatch: "
            f"expected={expected_index_sha} actual={actual_index_sha}"
        )
    payload = json.loads(index.read_text())
    if payload.get("artifact_count") != 65 or payload.get("requires_github_for_restore") is not False:
        raise SystemExit("recovered Frameworks archive is not the expected self-contained archive")

    result = {
        "schema": 1,
        "state": "PASS",
        "kind": "frameworks-6.30-retained-artifact-recovery",
        "artifact_count": 65,
        "downloaded": downloaded,
        "reused": reused,
        "archive_root": str(archive),
        "archive_index_sha256": actual_index_sha,
        "network_required_for_repair": downloaded > 0,
        "requires_github_for_restore_after_repair": False,
        "package_attempt_consumed": False,
        "sbuild_invoked": False,
        "vm_created": False,
        "jit_invoked": False,
        "canonical_package_state_effect": "none",
    }
    args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
