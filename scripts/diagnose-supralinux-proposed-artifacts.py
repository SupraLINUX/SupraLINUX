#!/usr/bin/env python3
"""Report exact retained-artifact availability for the current SupraLINUX-proposed plan."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.artifact_root.resolve(strict=True)
    if root.is_symlink() or not root.is_dir():
        raise SystemExit("artifact root must be a real directory")

    proc = subprocess.run(
        ["python3", "scripts/plan-supralinux-proposed.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    plan = json.loads(proc.stdout)
    rows = []
    for candidate in plan["candidates"]:
        retention = candidate.get("retention") or {}
        archive_root = retention.get("archive_root")
        digest = candidate["artifact_sha256"]
        if not isinstance(archive_root, str):
            raise SystemExit(f"{candidate['node']}: missing retention archive root")
        relative = Path(archive_root)
        if not relative.parts or relative.parts[0] != ".artifacts":
            raise SystemExit(f"{candidate['node']}: invalid retention archive root")
        path = root.joinpath(*relative.parts[1:]) / "sha256" / f"{digest}.zip"
        exists = path.is_file() and not path.is_symlink()
        actual = sha256(path) if exists else None
        state = "PRESENT" if actual == digest else ("DRIFT" if exists else "MISSING")
        rows.append(
            {
                "node": candidate["node"],
                "state": state,
                "artifact_id": candidate.get("artifact_id"),
                "artifact_sha256": digest,
                "path": str(path),
                "actual_sha256": actual,
                "github_recoverable": isinstance(candidate.get("artifact_id"), int),
            }
        )

    summary = {
        "schema": 1,
        "state": "PASS",
        "candidate_count": len(rows),
        "present": sum(row["state"] == "PRESENT" for row in rows),
        "missing": sum(row["state"] == "MISSING" for row in rows),
        "drift": sum(row["state"] == "DRIFT" for row in rows),
        "missing_github_recoverable": sum(
            row["state"] == "MISSING" and row["github_recoverable"] for row in rows
        ),
        "missing_offline_only": sum(
            row["state"] == "MISSING" and not row["github_recoverable"] for row in rows
        ),
        "rows": rows,
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
