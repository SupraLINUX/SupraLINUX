#!/usr/bin/env python3
"""Preserve an unsuccessful Attempt with its original package/infra classification."""
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


def record_interruption(args):
    """Record a host-captured interruption; never synthesize a guest result."""
    manifest = ROOT / "manifests/kde-plasma-package-build.json"
    campaign = json.loads(manifest.read_text())
    record = campaign["nodes"][args.node]
    assert campaign["authorized_nodes"] == [args.node] and record["state"] == "build-pending"
    subprocess.run(["sha256sum", "--check", "--quiet", "evidence-sha256.txt"], cwd=args.host_dir, check=True)
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    host = json.loads((args.host_dir / "host-result.json").read_text())
    run = json.loads((args.host_dir / "workflow-run-created.json").read_text())
    assert host["exit_code"] != 0 and run["head_sha"] == head
    assert str(run["id"]) == host["workflow_run_id"]
    payload = args.host_dir / "guest-files/workspace/evidence/authoritative-plasma-package"
    assert not (payload / "result.json").exists(), "Use the original guest result when available"
    built = json.loads((payload / "build-contract.json").read_text())["nodes"][args.node]
    assert built["packaging_sha256"] == record["packaging_sha256"]
    assert "Status: successful" in (payload / "sbuild.log").read_text()
    assert not any(line.startswith("E:") for line in (payload / "lintian.log").read_text().splitlines())
    assert "test bed setup" in (payload / "autopkgtest/log").read_text()
    assert not (payload / "autopkgtest/summary").read_text().strip(), "Completed tests require separate diagnosis"
    number = len(record["attempts"]) + 1
    historical = ROOT / f"manifests/evidence/plasma/{args.node}-attempt{number}"
    assert not historical.exists(), "Refusing to overwrite closed evidence"
    archive_root = ROOT / f".artifacts/plasma-{record['upstream_version']}/{args.node}-attempt{number}"
    archive_root.mkdir(parents=True, exist_ok=True)
    temporary = archive_root / "host-capture.zip"
    assert not temporary.exists()
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(payload.rglob("*")):
            if path.is_file():
                assert not path.is_symlink()
                archive.write(path, str(path.relative_to(payload)))
    digest = closure.sha(temporary)
    item = {"node": args.node, "package_version": record["version"], "artifact_sha256": digest, "payload_prefix": "packages/"}
    inspection = retention.inspect(temporary, item, record["source_package"])
    assert inspection["source_payload_verified"] and inspection["changes_payload_complete"]
    assert {b["package"]: b["architecture"] for b in inspection["binaries"] if not b["package"].endswith("-dbgsym")} == record["binary_packages"]
    stored = archive_root / "sha256" / f"{digest}.zip"
    stored.parent.mkdir(exist_ok=True)
    assert not stored.exists()
    temporary.rename(stored)
    historical.mkdir(parents=True)
    for origin, name in [(args.host_dir / "host-result.json", "host-result.json"),
                         (payload / "build-contract.json", "build-contract.json")]:
        shutil.copyfile(origin, historical / name)
    observation = {"kind": "host-recovered-interruption-observation", "schema": 1,
                   "runner_result_present": False, "node": args.node, "version": record["version"],
                   "state": "INFRA_INVALID", "source_commit": head,
                   "workflow_run_id": host["workflow_run_id"], "package_attempt_consumed": True,
                   "sbuild_result": "PASS", "lintian_result": "PASS", "autopkgtest_result": "INFRA_INVALID",
                   "observed_stage": "autopkgtest-testbed-setup", "downstream_eligible": False,
                   "host_result_sha256": closure.sha(historical / "host-result.json"),
                   "contract_sha256": closure.sha(historical / "build-contract.json"),
                   "host_evidence_manifest_sha256": closure.sha(args.host_dir / "evidence-sha256.txt"),
                   "archive_sha256": digest,
                   "files_sha256": {str(p.relative_to(payload)): closure.sha(p) for p in sorted(payload.rglob("*")) if p.is_file()},
                   "cause": args.cause, "repair": args.repair}
    closure.write(historical / "observation.json", observation)
    closure.write(archive_root / "index.json", {"kind": "interrupted-package-host-capture", "package_state": "INFRA_INVALID",
                                               "downstream_eligible": False, "inspection": inspection,
                                               "archive_sha256": digest, "host_seal_verified": True})
    record["attempts"].append({"attempt": number, "state": "INFRA_INVALID", "source_commit": head,
                               "package_attempt_consumed": True, "sbuild_result": "PASS", "lintian_result": "PASS",
                               "autopkgtest_result": "INFRA_INVALID", "workflow_run_id": run["id"], "workflow_job_id": args.job_id,
                               "artifact_id": None, "artifact_sha256": digest, "artifact_origin": "sealed-host-recovery",
                               "result_path": str((historical / "observation.json").relative_to(ROOT)),
                               "result_sha256": closure.sha(historical / "observation.json"),
                               "host_evidence_dir": str(args.host_dir),
                               "host_evidence_manifest_sha256": observation["host_evidence_manifest_sha256"],
                               "cause": args.cause, "repair": args.repair})
    campaign["retained_attempt_archives"].append({"node": args.node, "attempt": number,
                                                "archive_root": str(archive_root.relative_to(ROOT)),
                                                "archive_index_sha256": closure.sha(archive_root / "index.json")})
    closure.write(manifest, campaign)
    print(f"{args.node} Attempt {number}: interrupted package, sealed host payload retained; tests incomplete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("node")
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--artifact-meta", type=Path)
    parser.add_argument("--host-dir", type=Path, required=True)
    parser.add_argument("--job-id", type=int, required=True)
    parser.add_argument("--cause", required=True)
    parser.add_argument("--repair", required=True)
    parser.add_argument("--host-interruption", action="store_true")
    parser.add_argument("--verification-invalid", action="store_true")
    args = parser.parse_args()
    if args.host_interruption:
        record_interruption(args)
        return
    assert args.zip and args.artifact_meta
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
        assert result["state"] in {"FAIL", "INFRA_INVALID"} and result["package_attempt_consumed"] is True
        assert result["node"] == args.node and result["version"] == record["version"]
        assert result["source_commit"] == head == meta["workflow_run"]["head_sha"]
        assert result["workflow_run_id"] == host["workflow_run_id"] == str(meta["workflow_run"]["id"])
        for name, digest in result["files_sha256"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
        reported_state = result["state"]
        diagnosis = None
        if args.verification_invalid:
            assert result["state"] == "FAIL", "A false-negative diagnosis requires an original package FAIL"
            assert result["stage"] == "upstream-package-tests" and result["sbuild_result"] == "PASS"
            testing = importlib.machinery.SourceFileLoader("testing", str(ROOT / "scripts/plasma-package-testing.py")).load_module()
            corrected = testing.upstream_test_result(record, archive.read("sbuild.log").decode())
            assert corrected["state"] == "PASS"
            reported_state = "INFRA_INVALID"
            diagnosis = {"kind": "verification-gate-false-negative", "original_state": result["state"],
                         "original_result_sha256": hashlib.sha256(payload).hexdigest(),
                         "upstream_tests": corrected,
                         "candidate_outputs_retained": any(name.startswith("packages/") and name.endswith(".deb") for name in archive.namelist()),
                         "package_result": "incomplete; requires remaining package tests"}
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
    if diagnosis is not None:
        closure.write(path / "verification-diagnosis.json", diagnosis)
    archive_root = ROOT / f".artifacts/plasma-{record['upstream_version']}/{args.node}-attempt{number}"
    stored = archive_root / "sha256" / f"{closure.sha(args.zip)}.zip"
    stored.parent.mkdir(parents=True, exist_ok=True)
    if not stored.exists():
        shutil.copyfile(args.zip, stored)
    assert closure.sha(stored) == closure.sha(args.zip)
    closure.write(archive_root / "index.json", {
        "kind": "failed-package-attempt-archive", "package_state": reported_state, "downstream_eligible": False,
        "artifact_sha256": closure.sha(stored), "source_payload_verified": True,
        "node": args.node, "version": record["version"], "result_sha256": closure.sha(path / "result.json")})
    record["attempts"].append({
        "attempt": number, "state": reported_state, "original_state": result["state"],
        "sbuild_result": result["sbuild_result"],
        "lintian_result": result["lintian_result"], "autopkgtest_result": result["autopkgtest_result"],
        "package_attempt_consumed": True, "workflow_run_id": int(result["workflow_run_id"]),
        "workflow_job_id": args.job_id, "source_commit": head, "artifact_id": meta["id"],
        "artifact_sha256": closure.sha(stored), "result_path": str((path / "result.json").relative_to(ROOT)),
        "result_sha256": closure.sha(path / "result.json"), "host_evidence_dir": str(args.host_dir),
        "host_evidence_manifest_sha256": closure.sha(args.host_dir / "evidence-sha256.txt"),
        "cause": args.cause, "repair": args.repair})
    if diagnosis is not None:
        record["attempts"][-1].update(verification_diagnosis_path=str((path / "verification-diagnosis.json").relative_to(ROOT)),
                                      verification_diagnosis_sha256=closure.sha(path / "verification-diagnosis.json"))
    campaign["retained_attempt_archives"].append({"node": args.node, "attempt": number,
                                                "archive_root": str(archive_root.relative_to(ROOT)),
                                                "archive_index_sha256": closure.sha(archive_root / "index.json")})
    closure.write(manifest, campaign)
    print(f"{args.node} Attempt {number}: original {result["state"]} retained; classification {reported_state}; no downstream artifact admission")


if __name__ == "__main__":
    main()
