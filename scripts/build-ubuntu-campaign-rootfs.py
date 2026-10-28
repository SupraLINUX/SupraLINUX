#!/usr/bin/env python3
"""Build a frozen Ubuntu 26.04 buildd rootfs for a future SupraLINUX campaign."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import tarfile
from pathlib import Path
from urllib.parse import urlsplit

SNAPSHOT_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
SUITES = ("resolute", "resolute-updates", "resolute-security")
COMPONENTS = ("main", "universe")
FORBIDDEN_SDK = re.compile(
    r"^(libkf6|kf6-|qt6-|libqt6|qml6-|extra-cmake-modules$|cmake$|debhelper)"
)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def parse_snapshot(value: str) -> int:
    if not SNAPSHOT_RE.fullmatch(value):
        raise SystemExit("snapshot id must use YYYYMMDDTHHMMSSZ")
    instant = dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    return int(instant.timestamp())


def apt_lists_digest(archive: tarfile.TarFile) -> tuple[int, str]:
    rows: list[tuple[str, str]] = []
    for member in archive.getmembers():
        name = member.name.removeprefix("./")
        if not name.startswith("var/lib/apt/lists/") or not member.isfile():
            continue
        payload = archive.extractfile(member).read()
        rows.append((name, hashlib.sha256(payload).hexdigest()))
    if not rows:
        raise SystemExit("frozen rootfs does not retain APT package lists")
    canonical = "\n".join(f"{name}\t{digest}" for name, digest in sorted(rows)).encode()
    return len(rows), hashlib.sha256(canonical).hexdigest()


def inspect_rootfs(path: Path, snapshot_id: str) -> dict:
    with tarfile.open(path) as archive:
        members = {m.name.removeprefix("./"): m for m in archive.getmembers()}

        def read(name: str) -> bytes:
            member = members.get(name)
            if member is None or not member.isfile():
                raise SystemExit(f"missing rootfs metadata: {name}")
            return archive.extractfile(member).read()

        release = dict(
            line.split("=", 1)
            for line in read("usr/lib/os-release").decode().splitlines()
            if "=" in line
        )
        if not (
            release.get("ID") == "ubuntu"
            and release.get("VERSION_ID", "").strip('"') == "26.04"
            and release.get("VERSION_CODENAME") == "resolute"
        ):
            raise SystemExit(f"unexpected rootfs release: {release}")

        apt_config = read("etc/apt/apt.conf.d/99mmdebstrap").decode()
        expected = f'APT::Snapshot "{snapshot_id}";'
        if expected not in apt_config:
            raise SystemExit("frozen rootfs does not pin the requested APT snapshot")

        installed = []
        for stanza in read("var/lib/dpkg/status").decode().split("\n\n"):
            fields = {}
            for line in stanza.splitlines():
                if ": " in line and not line.startswith(" "):
                    key, value = line.split(": ", 1)
                    fields[key] = value
            if fields.get("Status") == "install ok installed":
                installed.append(
                    {
                        "package": fields["Package"],
                        "version": fields["Version"],
                        "architecture": fields["Architecture"],
                    }
                )
        forbidden = sorted(
            item["package"] for item in installed if FORBIDDEN_SDK.match(item["package"])
        )
        if forbidden:
            raise SystemExit(f"SDK packages preinstalled in frozen rootfs: {forbidden}")

        lists_count, lists_digest = apt_lists_digest(archive)
        return {
            "release": {
                "id": "ubuntu",
                "version_id": "26.04",
                "codename": "resolute",
            },
            "installed_base_packages": sorted(installed, key=lambda row: row["package"]),
            "apt_lists_file_count": lists_count,
            "apt_lists_digest": lists_digest,
            "frameworks_and_qt_sdk_preinstalled": False,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--mirror", default="https://archive.ubuntu.com/ubuntu")
    args = parser.parse_args()

    epoch = parse_snapshot(args.snapshot_id)
    mirror = urlsplit(args.mirror)
    if not (
        mirror.scheme == "https"
        and mirror.netloc == "archive.ubuntu.com"
        and mirror.path.rstrip("/") == "/ubuntu"
        and not mirror.query
        and not mirror.fragment
    ):
        raise SystemExit("only the official HTTPS Ubuntu archive is admitted")
    if args.output.exists():
        raise SystemExit(f"refusing to replace existing rootfs: {args.output}")
    if args.evidence.exists():
        raise SystemExit(f"refusing to replace existing evidence: {args.evidence}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)

    sources = [
        f"deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] "
        f"{args.mirror.rstrip('/')} {suite} {' '.join(COMPONENTS)}"
        for suite in SUITES
    ]
    command = [
        "mmdebstrap",
        "--mode=unshare",
        "--variant=buildd",
        "--architectures=amd64",
        "--components=" + ",".join(COMPONENTS),
        "--skip=output/mknod",
        "--skip=cleanup/apt/lists",
        "--format=tar",
        f'--aptopt=APT::Snapshot "{args.snapshot_id}"',
        '--aptopt=Acquire::Languages "none"',
        "--keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg",
        "resolute",
        str(args.output),
        *sources,
    ]
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = str(epoch)
    completed = subprocess.run(command, env=env, text=True, capture_output=True)
    log = args.evidence.with_suffix(".mmdebstrap.log")
    log.write_text(completed.stdout + completed.stderr)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    inspection = inspect_rootfs(args.output, args.snapshot_id)
    result = {
        "schema": 1,
        "state": "PASS",
        "kind": "frozen-ubuntu-campaign-buildd-rootfs",
        "provider_platform": "ubuntu-resolute",
        "snapshot_id": args.snapshot_id,
        "snapshot_service": "https://snapshot.ubuntu.com/ubuntu/",
        "mirror": args.mirror,
        "suites": list(SUITES),
        "components": list(COMPONENTS),
        "architecture": "amd64",
        "source_date_epoch": epoch,
        "rootfs_sha256": sha256(args.output),
        "apt_lists_retained": True,
        "sbuild_default_archive_policy": {
            "apt_update": False,
            "apt_distupgrade": False,
            "extra_package_repository_update": "still-required-by-sbuild",
        },
        "package_attempt_consumed": False,
        **inspection,
    }
    args.evidence.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
