"""Compare two independent resolutions and bind the first verification evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_snapshot import candidate, reconcile


def compare(first, second, verification, lock_digest):
    if first != second:
        raise ValueError("Independent snapshot locks differ")
    if (verification.get("schema_version") != 1
            or verification.get("kind") != "snapshot-signature-evidence"
            or verification.get("candidate_lock_sha256") != lock_digest
            or verification.get("builder") != first["builder"]
            or verification.get("package_signatures_verified") is not True
            or verification.get("release_signed") is not False):
        raise ValueError("Verification evidence does not match the candidate")
    rows = ["\t".join(p[k] for k in ("name", "sha256", "signer"))
            for p in verification["packages"]]
    reconcile(first["packages"], rows)
    return {"schema_version": 1, "kind": "snapshot-resolution-comparison",
            "candidate_lock_sha256": lock_digest,
            "snapshot": first["snapshot"], "package_count": len(first["packages"]),
            "independent_resolution_equal": True,
            "first_resolution_signatures_verified": True,
            "rootfs_reproducible": False, "release_signed": False}


def main():
    parser = argparse.ArgumentParser()
    for name in ("config", "first", "second", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    first = candidate(args.config, args.first)
    second = candidate(args.config, args.second)
    digest = hashlib.sha256((args.first / "snapshot-lock.json").read_bytes()).hexdigest()
    verification = json.loads((args.first / "snapshot-verification.json").read_text())
    result = compare(first, second, verification, digest)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "resolution-comparison.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(f"Independent resolutions agree: {result['package_count']} packages")


if __name__ == "__main__":
    main()
