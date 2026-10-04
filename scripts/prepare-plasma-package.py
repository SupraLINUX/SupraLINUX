#!/usr/bin/env python3
"""Materialize an explicitly reviewed packaging overlay on verified KDE sources."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def packaging_hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def contract(node):
    campaign = json.loads((ROOT / "manifests/kde-plasma-package-build.json").read_text())
    record = campaign["nodes"][node]
    level = json.loads((ROOT / "manifests/kde-plasma-level0.json").read_text())["nodes"][node]
    assert record["packaging_review"] == "PASS", "Packaging requires individual review"
    assert record["version"] == level["candidate_package_version"], "Candidate version mismatch"
    assert record["upstream_sha256"] == level["upstream_source_sha256"], "Source mismatch"
    assert packaging_hashes(ROOT / record["packaging_path"]) == record["packaging_sha256"], "Packaging inputs changed"
    return campaign, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("node")
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _, record = contract(args.node)
    assert hashlib.sha256(args.upstream.read_bytes()).hexdigest() == record["upstream_sha256"], "Upstream tarball digest"
    assert not args.output.exists(), "Refusing to overwrite prepared sources"
    args.output.mkdir(parents=True)
    source_name = record["source_package"]
    upstream_version = record["upstream_version"]
    orig = args.output / f"{source_name}_{upstream_version}.orig.tar.xz"
    shutil.copyfile(args.upstream, orig)
    with tarfile.open(orig) as archive:
        prefix = f"{args.node}-{upstream_version}"
        assert all(m.name == prefix or m.name.startswith(prefix + "/") for m in archive), "Unexpected source root"
        archive.extractall(args.output, filter="data")
    source = args.output / prefix
    shutil.copytree(ROOT / record["packaging_path"], source / "debian",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    actual = subprocess.check_output(["dpkg-parsechangelog", "-l", str(source / "debian/changelog"), "-S", "Version"], text=True).strip()
    assert actual == record["version"], "Changelog version mismatch"
    subprocess.run(["dpkg-source", "-b", str(source)], cwd=args.output, check=True)
    print(args.output / f"{source_name}_{record['version'].split(':')[-1]}.dsc")


if __name__ == "__main__":
    main()
