"""Convert a Pacman-resolved empty-root transaction into a candidate lock.
This is not an installed root or a signed release manifest.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

ORIGIN = "https://archive.archlinux.org/repos"
FIELDS = ("repository", "name", "version", "arch", "sha256", "filename", "url")

def validate_config(cfg):
    if cfg["schema_version"] != 1 or cfg["architecture"] != "x86_64":
        raise ValueError("Unsupported configuration")
    if not re.fullmatch(r"\d{4}/\d{2}/\d{2}", cfg["snapshot"]):
        raise ValueError("Snapshot must be a fixed UTC date")
    datetime.strptime(cfg["snapshot"], "%Y/%m/%d")
    repos = cfg["repositories"]
    if repos != ["core", "extra"]:
        raise ValueError("Unexpected repository set")
    if not re.fullmatch(r"docker\.io/library/archlinux@sha256:[0-9a-f]{64}", cfg["builder"]):
        raise ValueError("Builder must be digest-pinned")
    if not cfg["packages"] or any(not re.fullmatch(r"[a-z0-9][a-z0-9+_.-]*", p) for p in cfg["packages"]):
        raise ValueError("Invalid package selection")
    return cfg

def lock(cfg, lines, database_hashes):
    cfg = validate_config(cfg)
    packages = {}
    for line in lines:
        parts = line.rstrip("\n").split("|")
        if len(parts) != len(FIELDS):
            raise ValueError("Malformed Pacman transaction row")
        item = dict(zip(FIELDS, parts))
        repo, name = item["repository"], item["name"]
        if repo not in cfg["repositories"] or not re.fullmatch(r"[a-z0-9][a-z0-9+_.-]*", name):
            raise ValueError("Unexpected repository or package")
        if name in packages or item["arch"] not in ("any", cfg["architecture"]):
            raise ValueError("Duplicate or incompatible package")
        if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError("Invalid package digest")
        if not re.fullmatch(r"[A-Za-z0-9+_.-]+\.pkg\.tar\.(zst|xz)", item["filename"]):
            raise ValueError("Invalid package filename")
        expected = f"{ORIGIN}/{cfg['snapshot']}/{repo}/os/x86_64/{item['filename']}"
        if item["url"] != expected:
            raise ValueError("Package not from configured snapshot")
        packages[name] = item
    if not set(cfg["packages"]) <= packages.keys():
        raise ValueError("Requested packages missing")
    if set(database_hashes) != set(cfg["repositories"]):
        raise ValueError("Missing repository database hash")
    if any(not re.fullmatch(r"[0-9a-f]{64}", h) for h in database_hashes.values()):
        raise ValueError("Invalid database digest")
    return {"schema_version": 1, "kind": "candidate-package-lock",
            "architecture": cfg["architecture"], "snapshot": cfg["snapshot"],
            "builder": cfg["builder"], "requested": cfg["packages"],
            "databases": database_hashes, "packages": [packages[n] for n in sorted(packages)],
            "package_signatures_verified": False, "release_signed": False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("config",type=Path)
    ap.add_argument("evidence",type=Path)
    args=ap.parse_args()
    cfg=json.loads(args.config.read_text())
    evidence=args.evidence
    hashes={repo:hashlib.sha256((evidence/f"{repo}.db").read_bytes()).hexdigest() for repo in cfg["repositories"]}
    result=lock(cfg,(evidence/"transaction.txt").read_text().splitlines(),hashes)
    (evidence/"snapshot-lock.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(f"Resolved {len(result['packages'])} packages from {result['snapshot']}")
    print("Metadata candidate only; package signatures and image build not yet verified.")

if __name__ == "__main__":
    main()
