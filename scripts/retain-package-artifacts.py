#!/usr/bin/env python3
"""Verify exact package identities and retain complete artifact ZIPs locally."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fields(text):
    result = {}
    current = None
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*)$", line)
        if match:
            current, value = match.groups()
            result[current] = value
        elif line.startswith((" ", "\t")) and current:
            result[current] += "\n" + line.strip()
    return result


def inspect(path, item, source, allow_legacy_source_gaps=False):
    if sha256(path) != item["artifact_sha256"]:
        raise ValueError(f"{item['node']}: artifact digest mismatch")
    version = item["package_version"]
    with zipfile.ZipFile(path) as archive:
        members = {Path(name).name: name for name in archive.namelist() if not name.endswith("/")}
        if len(members) != len([n for n in archive.namelist() if not n.endswith("/")]):
            raise ValueError(f"{item['node']}: duplicate artifact basenames")
        changes = [name for name in members if name.endswith(".changes")]
        if len(changes) != 1:
            raise ValueError(f"{item['node']}: expected one source-scoped .changes")
        metadata = fields(archive.read(members[changes[0]]).decode())
        if metadata.get("Source", "").split(" ")[0] != source or metadata.get("Version") != version:
            raise ValueError(f"{item['node']}: .changes does not identify {source} {version}")
        source_control = None
        for suffix in (".dsc", ".buildinfo"):
            names = [name for name in members if name.endswith(suffix)]
            if suffix == ".dsc" and not names and allow_legacy_source_gaps:
                continue
            if len(names) != 1:
                raise ValueError(f"{item['node']}: missing/ambiguous {suffix} evidence")
            control = fields(archive.read(members[names[0]]).decode())
            if control.get("Source", "").split(" ")[0] != source or control.get("Version") != version:
                raise ValueError(f"{item['node']}: {suffix} identity mismatch")
            if suffix == ".dsc":
                source_control = control
        missing_debug_packages = []
        for control in (metadata, source_control):
            if control is None:
                continue
            checksums = control.get("Checksums-Sha256", "").splitlines()
            if not checksums:
                raise ValueError(f"{item['node']}: missing source/binary checksum closure")
            for line in checksums:
                if not line.strip():
                    continue
                digest, size, name = line.split()
                if name not in members:
                    # Early lanes intentionally uploaded .deb but not dbgsym .ddeb.
                    # Preserve this limitation instead of claiming a complete changes closure.
                    if control is metadata and name.endswith(".ddeb"):
                        missing_debug_packages.append(name)
                        continue
                    raise ValueError(f"{item['node']}: missing retained payload {name}")
                payload = archive.read(members[name])
                if hashlib.sha256(payload).hexdigest() != digest or len(payload) != int(size):
                    raise ValueError(f"{item['node']}: checksum mismatch for {name}")
        binaries = []
        with tempfile.TemporaryDirectory(prefix="supralinux-artifact-identity-") as directory:
            for name in sorted(members):
                if not name.endswith((".deb", ".ddeb")):
                    continue
                deb = Path(directory) / name
                deb.write_bytes(archive.read(members[name]))
                control = fields(subprocess.check_output(["dpkg-deb", "--field", str(deb)], text=True))
                actual_source = control.get("Source", control.get("Package", "")).split(" ")[0]
                if actual_source != source or control.get("Version") != version:
                    raise ValueError(f"{item['node']}: binary identity mismatch for {name}")
                if control.get("Architecture") not in {"amd64", "all"}:
                    raise ValueError(f"{item['node']}: unexpected binary architecture for {name}")
                binaries.append({"package": control["Package"], "version": version,
                                 "architecture": control["Architecture"], "file": name})
                deb.unlink()
        if not binaries:
            raise ValueError(f"{item['node']}: artifact contains no binary packages")
    return {**item, "source_package": source, "binaries": binaries,
            "source_payload_verified": source_control is not None, "buildinfo_verified": True,
            "changes_payload_complete": not missing_debug_packages,
            "missing_debug_packages": missing_debug_packages,
            "evidence_scope": "retained-build-evidence; not new authoritative certification"}


def retain(plan_path, dag_path, cache, archive, verify_only=False, restore_cache=False,
           allow_legacy_source_gaps=False):
    plan = json.loads(plan_path.read_text())
    dag = json.loads(dag_path.read_text())
    results = []
    for item in plan["items"]:
        stored = archive / "sha256" / f"{item['artifact_sha256']}.zip"
        download = cache / f"{item['artifact_id']}.zip" if cache else None
        path = stored if stored.is_file() else download
        if path is None or not path.is_file():
            raise ValueError(f"{item['node']}: retained artifact bytes unavailable")
        source = dag["nodes"][item["node"]].get("source_package")
        if not source:
            for contract_path in sorted(dag_path.parent.glob("kde-tier*-package-contracts.json")):
                contract = json.loads(contract_path.read_text()).get("nodes", {}).get(item["node"], {})
                source = contract.get("source_package")
                if source:
                    break
        if not source:
            control = dag_path.parent.parent / "packages/kde" / item["node"] / "debian/control"
            source = fields(control.read_text()).get("Source")
        if not source:
            raise ValueError(f"{item['node']}: no declared source-package identity")
        result = inspect(path, item, source, allow_legacy_source_gaps)
        result["archive_path"] = str(stored.relative_to(archive))
        results.append(result)
        if not verify_only:
            stored.parent.mkdir(parents=True, exist_ok=True)
            if not stored.exists():
                temporary = stored.with_suffix(".zip.tmp")
                shutil.copyfile(path, temporary)
                if sha256(temporary) != item["artifact_sha256"]:
                    raise ValueError(f"{item['node']}: archive copy verification failed")
                temporary.replace(stored)
            if restore_cache and download:
                if download.exists() and sha256(download) != item["artifact_sha256"]:
                    raise ValueError(f"{item['node']}: refusing to overwrite a conflicting download")
                if not download.exists():
                    download.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(stored, download)
        print(f"Verified {item['node']} {item['package_version']}: {len(result['binaries'])} binaries", flush=True)
    index = {"schema": 1, "kind": "retained-package-artifact-archive", "result": "PASS",
             "plan_sha256": sha256(plan_path), "artifact_count": len(results),
             "binary_count": sum(len(item["binaries"]) for item in results), "items": results,
             "requires_github_for_restore": False, "off_host_backup_verified": False}
    index["source_complete_artifact_count"] = sum(item["source_payload_verified"] for item in results)
    index["legacy_source_gaps"] = [item["node"] for item in results if not item["source_payload_verified"]]
    if index["legacy_source_gaps"]:
        index["result"] = "PASS_WITH_LEGACY_SOURCE_GAPS"
    if not verify_only:
        archive.mkdir(parents=True, exist_ok=True)
        temporary = archive / "index.json.tmp"
        temporary.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
        temporary.replace(archive / "index.json")
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--dag", type=Path, default=ROOT / "manifests/kde-dag.json")
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--restore-cache", action="store_true")
    parser.add_argument("--allow-legacy-source-gaps", action="store_true",
                        help="retain incomplete historical source evidence while recording the gap")
    args = parser.parse_args()
    result = retain(args.plan, args.dag, args.cache, args.archive, args.verify_only, args.restore_cache,
                    args.allow_legacy_source_gaps)
    print(f"Artifact archive: {result['result']}; artifacts={result['artifact_count']} binaries={result['binary_count']}")


if __name__ == "__main__":
    main()
