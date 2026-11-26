"""Bind the S04 input to the verified, independently resolved snapshot."""
import argparse
import hashlib
import json
from pathlib import Path

from compare_snapshot import compare
from verify_snapshot import candidate


def validate_installed(packages, rows):
    expected = {p["name"]: p["version"] for p in packages}
    actual = {}
    for row in rows:
        name, version = row.split()
        if name in actual:
            raise ValueError("Duplicate installed package")
        actual[name] = version
    if actual != expected:
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        changed = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
        raise ValueError(f"Installed closure differs: missing={missing}, extra={extra}, changed={changed}")
    return len(actual)


def main():
    p = argparse.ArgumentParser()
    for name in ("config", "evidence", "comparison"):
        p.add_argument(name, type=Path)
    p.add_argument("--check-installed", action="store_true")
    a = p.parse_args()
    lock = candidate(a.config, a.evidence)
    digest = hashlib.sha256((a.evidence / "snapshot-lock.json").read_bytes()).hexdigest()
    verified = json.loads((a.evidence / "snapshot-verification.json").read_text())
    expected = compare(lock, lock, verified, digest)
    if json.loads((a.comparison / "resolution-comparison.json").read_text()) != expected:
        raise ValueError("Comparison evidence does not match lock")
    if a.check_installed:
        count = validate_installed(lock["packages"], (a.evidence / "installed-packages.txt").read_text().splitlines())
        result = {"kind": "experimental-rootfs-build", "schema_version": 1,
                  "candidate_lock_sha256": digest, "installed_package_count": count,
                  "installed_closure_matches": True, "boot_verified": False,
                  "rootfs_reproducible": False, "release_signed": False}
        (a.evidence / "rootfs-report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(f"Installed closure matches: {count} packages")
    else:
        (a.evidence / "rootfs-input.tsv").write_text("".join(
            f"{pkg['filename']}\t{pkg['sha256']}\n" for pkg in lock["packages"]))
        # Bind the exact builder instead of trusting a stale artifact text file.
        (a.evidence / "build-input.txt").write_text(lock["builder"] + "\n")


if __name__ == "__main__":
    main()
