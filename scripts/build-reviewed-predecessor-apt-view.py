#!/usr/bin/env python3
"""Build an exact per-node APT view from already admitted predecessor binaries."""
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


def deb_field(path: Path, field: str) -> str:
    return subprocess.check_output(
        ["dpkg-deb", "-f", str(path), field], text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit(f"refusing to replace existing APT view: {args.output}")
    if args.manifest.exists():
        raise SystemExit(f"refusing to replace existing manifest: {args.manifest}")

    admission = json.loads(args.admission.read_text())
    if admission.get("state") != "PASS" or admission.get("cache_only") is not True:
        raise SystemExit("predecessor admission is not an eligible PASS cache receipt")
    selected = admission.get("selected")
    if not isinstance(selected, list) or not selected:
        raise SystemExit("predecessor admission has no selected binaries")

    pool = args.output / "pool"
    pool.mkdir(parents=True)
    rows = []
    seen_packages = set()
    seen_files = set()

    for item in sorted(selected, key=lambda row: row["package"]):
        package = item["package"]
        version = item["version"]
        architecture = item["architecture"]
        source_package = item["source_package"]
        expected_sha = item["sha256"]
        source = Path(item["path"]).resolve()

        if package in seen_packages:
            raise SystemExit(f"duplicate selected package: {package}")
        seen_packages.add(package)
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"invalid selected binary path: {source}")
        if sha256(source) != expected_sha:
            raise SystemExit(f"selected binary digest drift: {package}")

        actual = {
            "package": deb_field(source, "Package"),
            "version": deb_field(source, "Version"),
            "architecture": deb_field(source, "Architecture"),
            "source_package": deb_field(source, "Source").split(" ", 1)[0],
        }
        expected = {
            "package": package,
            "version": version,
            "architecture": architecture,
            "source_package": source_package,
        }
        if actual != expected:
            raise SystemExit(
                f"selected binary identity drift: expected={expected} actual={actual}"
            )

        filename = f"{package}_{version.replace(':', '%3a')}_{architecture}.deb"
        if filename in seen_files:
            raise SystemExit(f"duplicate APT view filename: {filename}")
        seen_files.add(filename)
        target = pool / filename
        try:
            os.link(source, target)
            materialization = "hardlink"
        except OSError:
            shutil.copyfile(source, target)
            materialization = "copy"
        if sha256(target) != expected_sha:
            raise SystemExit(f"APT view materialization digest drift: {package}")

        rows.append(
            {
                **expected,
                "sha256": expected_sha,
                "source_path": str(source),
                "repo_path": str(target.relative_to(args.output)),
                "materialization": materialization,
            }
        )

    packages = subprocess.check_output(
        ["apt-ftparchive", "packages", "pool"], cwd=args.output, text=True
    )
    packages_path = args.output / "Packages"
    packages_path.write_text(packages)
    if not packages.strip():
        raise SystemExit("apt-ftparchive produced an empty Packages index")

    indexed = {}
    current = {}
    for raw in packages.splitlines() + [""]:
        if not raw:
            if current:
                indexed[current["Package"]] = current
                current = {}
            continue
        if raw.startswith(" "):
            continue
        key, value = raw.split(": ", 1)
        current[key] = value
    if set(indexed) != seen_packages:
        raise SystemExit(
            f"APT Packages set mismatch: expected={sorted(seen_packages)} "
            f"actual={sorted(indexed)}"
        )

    for row in rows:
        stanza = indexed[row["package"]]
        if stanza.get("Version") != row["version"]:
            raise SystemExit(f"APT index version mismatch: {row['package']}")
        if stanza.get("Architecture") != row["architecture"]:
            raise SystemExit(f"APT index architecture mismatch: {row['package']}")
        if stanza.get("SHA256") != row["sha256"]:
            raise SystemExit(f"APT index digest mismatch: {row['package']}")
        if stanza.get("Filename") != row["repo_path"]:
            raise SystemExit(f"APT index filename mismatch: {row['package']}")

    release = subprocess.check_output(
        ["apt-ftparchive", "release", "."], cwd=args.output, text=True
    )
    (args.output / "Release").write_text(release)

    manifest = {
        "schema": 1,
        "state": "PASS",
        "kind": "exact-reviewed-predecessor-apt-view",
        "cache_only": True,
        "admission_path": str(args.admission),
        "admission_sha256": sha256(args.admission),
        "package_count": len(rows),
        "packages_index_sha256": sha256(packages_path),
        "release_sha256": sha256(args.output / "Release"),
        "packages": rows,
        "allows_unselected_milestone_packages": False,
        "frameworks_and_qt_sdk_preinstalled_in_rootfs": False,
        "package_attempt_consumed": False,
        "solver_role": "replace many --extra-package arguments with one exact local APT view",
        "publication_role": "none",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(
        "Exact predecessor APT view: PASS; "
        f"packages={len(rows)} index_sha256={manifest['packages_index_sha256']}"
    )


if __name__ == "__main__":
    main()
