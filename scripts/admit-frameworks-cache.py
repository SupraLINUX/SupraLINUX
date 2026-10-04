#!/usr/bin/env python3
"""Verify a milestone payload and select only explicitly contracted build inputs."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def admit(payload, record, dag, current_plan):
    provenance = dict(line.split("=", 1) for line in
                      (payload / "checkpoint-manifest.txt").read_text().splitlines() if "=" in line)
    assert provenance["cache_only"] == "yes"
    assert provenance["framework_packages_preinstalled_in_sbuild_rootfs"] == "no"
    for relative, key in [("artifact-plan.json", "artifact_plan_sha256"),
                          ("package-pool.json", "package_pool_sha256"),
                          ("repo/Packages", "packages_index_sha256")]:
        assert digest(payload / relative) == provenance[key], f"Corrupt cache metadata: {relative}"
    assert (payload / "artifact-plan.json").read_bytes() == current_plan, "Stale Frameworks artifact plan"
    pool = json.loads((payload / "package-pool.json").read_text())
    assert pool["package_count"] == len(pool["packages"])
    actual_files = {p.name for p in (payload / "repo/pool").glob("*.deb")}
    assert actual_files == {item["file"] for item in pool["packages"]}, "Unexpected cache binaries"
    by_identity = {}
    for item in pool["packages"]:
        path = payload / "repo/pool" / item["file"]
        assert path.parent == payload / "repo/pool" and path.is_file() and not path.is_symlink()
        assert digest(path) == item["sha256"], f"Corrupt cache binary: {path.name}"
        assert path.stat().st_size == item["size"]
        identity = tuple(subprocess.check_output(["dpkg-deb", "-f", str(path), field], text=True).strip()
                         for field in ["Package", "Version", "Architecture"])
        assert identity == (item["package"], item["version"], item["architecture"]), "Cache identity mismatch"
        assert identity not in by_identity, "Duplicate cache identity"
        by_identity[identity] = path
    selected = []
    for node, predecessor in record["frameworks_predecessors"].items():
        canonical = dag["nodes"][node]
        assert canonical["state"] == "PASS" and canonical.get("downstream_eligible") is not False
        assert canonical["package_version"] == predecessor["version"]
        assert canonical["source_package"] == predecessor["source_package"]
        assert predecessor["binaries"], "Empty predecessor binary contract"
        for binary in predecessor["binaries"]:
            key = (binary["package"], predecessor["version"], binary["architecture"])
            assert key in by_identity, f"Required predecessor missing: {key}"
            path = by_identity[key]
            assert digest(path) == binary["sha256"], "Predecessor digest differs from reviewed contract"
            source = subprocess.check_output(["dpkg-deb", "-f", str(path), "Source"], text=True).strip()
            assert source.split(" ")[0] == predecessor["source_package"], "Predecessor source mismatch"
            selected.append({"node": node, "path": str(path), "source_package": predecessor["source_package"],
                             "version": predecessor["version"], **binary})
    assert len({item["path"] for item in selected}) == len(selected), "Duplicate selected predecessor"
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("node")
    parser.add_argument("--payload", type=Path, default=Path("/var/lib/supralinux/milestones/frameworks-6.30"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    campaign = json.loads((ROOT / "manifests/kde-plasma-package-build.json").read_text())
    assert campaign["execution_checkpoint"] == "frameworks-6.30-pass"
    selected = admit(args.payload, campaign["nodes"][args.node],
                     json.loads((ROOT / "manifests/kde-dag.json").read_text()),
                     subprocess.check_output(["python3", str(ROOT / "scripts/plan-frameworks-milestone.py")]))
    args.output.write_text(json.dumps({"state": "PASS", "cache_only": True, "selected": selected}, indent=2) + "\n")
    print(f"Frameworks cache admission: PASS; selected binaries={len(selected)}")


if __name__ == "__main__":
    main()
