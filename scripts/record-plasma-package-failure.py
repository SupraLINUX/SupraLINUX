#!/usr/bin/env python3
"""Preserve a valid failed Attempt without admitting its artifacts downstream."""
import argparse
import hashlib
import importlib.machinery
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
closure = importlib.machinery.SourceFileLoader("closure", str(ROOT / "scripts/close-plasma-package-evidence.py")).load_module()
retention = importlib.machinery.SourceFileLoader("retention", str(ROOT / "scripts/retain-package-artifacts.py")).load_module()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("node")
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--artifact-meta", type=Path, required=True)
    parser.add_argument("--host-dir", type=Path, required=True)
    parser.add_argument("--job-id", type=int, required=True)
    parser.add_argument("--cause", required=True)
    parser.add_argument("--repair", required=True)
    args = parser.parse_args()
    manifest = ROOT / "manifests/kde-plasma-package-build.json"
    campaign = json.loads(manifest.read_text())
    record = campaign["nodes"][args.node]
    assert campaign["authorized_nodes"] == [args.node] and record["state"] == "build-pending"
    meta = json.loads(args.artifact_meta.read_text())
    assert closure.sha(args.zip) == meta["digest"].removeprefix("sha256:")
    host = json.loads((args.host_dir / "host-result.json").read_text())
    assert host["exit_code"] != 0
    subprocess.run(["sha256sum", "--check", "--quiet", "evidence-sha256.txt"], cwd=args.host_dir, check=True)
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    with zipfile.ZipFile(args.zip) as archive:
        payload = archive.read("result.json")
        result = json.loads(payload)
        assert result["state"] == "FAIL" and result["package_attempt_consumed"] is True
        assert result["node"] == args.node and result["version"] == record["version"]
        assert result["source_commit"] == head == meta["workflow_run"]["head_sha"]
        assert result["workflow_run_id"] == host["workflow_run_id"] == str(meta["workflow_run"]["id"])
        for name, digest in result["files_sha256"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
        contract = archive.read("build-contract.json")
        assert json.loads(contract)["nodes"][args.node]["packaging_sha256"] == record["packaging_sha256"]
        sources = [name for name in archive.namelist() if name.startswith("packages/") and name.endswith(".dsc")]
        assert len(sources) == 1
        dsc = retention.fields(archive.read(sources[0]).decode())
        assert dsc["Source"] == record["source_package"] and dsc["Version"] == record["version"]
        for line in dsc["Checksums-Sha256"].splitlines():
            if not line.strip():
                continue
            digest, size, name = line.split()
            data = archive.read("packages/" + name)
            assert hashlib.sha256(data).hexdigest() == digest and len(data) == int(size)
    number = len(record["attempts"]) + 1
    path = ROOT / f"manifests/evidence/plasma/{args.node}-attempt{number}"
    assert not path.exists(), "Refusing to overwrite historical evidence"
    path.mkdir(parents=True)
    (path / "result.json").write_bytes(payload)
    (path / "build-contract.json").write_bytes(contract)
    archive_root = ROOT / f".artifacts/plasma-{record['upstream_version']}/{args.node}-attempt{number}"
    stored = archive_root / "sha256" / f"{closure.sha(args.zip)}.zip"
    stored.parent.mkdir(parents=True, exist_ok=True)
    if not stored.exists():
        shutil.copyfile(args.zip, stored)
    assert closure.sha(stored) == closure.sha(args.zip)
    closure.write(archive_root / "index.json", {
        "kind": "failed-package-attempt-archive", "package_state": "FAIL", "downstream_eligible": False,
        "artifact_sha256": closure.sha(stored), "source_payload_verified": True,
        "node": args.node, "version": record["version"], "result_sha256": closure.sha(path / "result.json")})
    record["attempts"].append({
        "attempt": number, "state": "FAIL", "sbuild_result": result["sbuild_result"],
        "lintian_result": result["lintian_result"], "autopkgtest_result": result["autopkgtest_result"],
        "package_attempt_consumed": True, "workflow_run_id": int(result["workflow_run_id"]),
        "workflow_job_id": args.job_id, "source_commit": head, "artifact_id": meta["id"],
        "artifact_sha256": closure.sha(stored), "result_path": str((path / "result.json").relative_to(ROOT)),
        "result_sha256": closure.sha(path / "result.json"), "host_evidence_dir": str(args.host_dir),
        "host_evidence_manifest_sha256": closure.sha(args.host_dir / "evidence-sha256.txt"),
        "cause": args.cause, "repair": args.repair})
    campaign["retained_attempt_archives"].append({"node": args.node, "attempt": number,
                                                "archive_root": str(archive_root.relative_to(ROOT)),
                                                "archive_index_sha256": closure.sha(archive_root / "index.json")})
    closure.write(manifest, campaign)
    print(f"{args.node} Attempt {number}: original FAIL retained; no downstream artifact admission")


if __name__ == "__main__":
    main()
