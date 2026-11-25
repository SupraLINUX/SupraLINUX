"""S03 evidence adapter. The candidate lock is immutable; no release promotion."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from snapshot_lock import validate_config, lock, validate_database, FIELDS


def candidate(config, evidence):
    cfg = validate_config(json.loads(config.read_text()))
    data = json.loads((evidence / "snapshot-lock.json").read_text())
    hashes = {repo: hashlib.sha256((evidence / f"{repo}.db").read_bytes()).hexdigest()
              for repo in cfg["repositories"]}
    rows = ["|".join(p[k] for k in FIELDS) for p in data["packages"]]
    rebuilt = lock(cfg, rows, hashes)
    rebuilt["database_metadata_matched"] = validate_database(rebuilt, evidence)
    if data != rebuilt:
        raise ValueError("Candidate lock differs from validated metadata")
    return data


def reconcile(packages, lines):
    expected = {p["name"]: p["sha256"] for p in packages}
    verified = {}
    for line in lines:
        name, digest, fingerprint = line.split("\t")
        if (name in verified or expected.get(name) != digest
                or not re.fullmatch(r"[A-F0-9]{40,64}", fingerprint)):
            raise ValueError("Unexpected signature evidence")
        verified[name] = {"name": name, "sha256": digest, "signer": fingerprint}
    if not expected or verified.keys() != expected.keys():
        raise ValueError("Incomplete verification evidence")
    return [verified[n] for n in sorted(verified)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "report"])
    parser.add_argument("config", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    data = candidate(args.config, args.evidence)
    packages = data["packages"]
    if args.phase == "prepare":
        rows = ["\t".join(p[k] for k in ("name", "sha256", "url")) for p in packages]
        (args.evidence / "verification-input.tsv").write_text("\n".join(rows) + "\n")
        return
    verified = reconcile(packages, (args.evidence / "verified-packages.tsv").read_text().splitlines())
    report = {"schema_version": 1, "kind": "snapshot-signature-evidence",
              "candidate_lock_sha256": hashlib.sha256(
                  (args.evidence / "snapshot-lock.json").read_bytes()).hexdigest(),
              "builder": data["builder"], "keyring": (
                  args.evidence / "verification-keyring.txt").read_text().strip(),
              "packages": verified, "package_signatures_verified": True,
              "release_signed": False}
    (args.evidence / "snapshot-verification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
