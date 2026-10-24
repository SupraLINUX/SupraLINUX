#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/kde-plasma-level0-materialization-preflight"
OUT.mkdir(parents=True, exist_ok=True)

def run(cmd, cwd=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def tree_hash(root):
    h = hashlib.sha256()
    root = Path(root)
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            payload = ("L\0" + rel + "\0" + os.readlink(path)).encode()
        elif path.is_file():
            payload = ("F\0" + rel + "\0" + sha256(path)).encode()
        else:
            continue
        h.update(payload)
        h.update(b"\n")
    return h.hexdigest()

def write_result(data):
    (OUT / "result.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

definition = json.loads((ROOT / "manifests/kde-plasma-level0-materialization-preflight.json").read_text())
sample = definition["sample"]["source_package"]
base = {
    "schema": 1,
    "node": "plasma-level0-materialization-infrastructure-preflight",
    "run_kind": "infrastructure-preflight",
    "mechanism": definition["mechanism"],
    "authoritative": False,
    "package_execution_started": False,
    "package_attempted": False,
    "consumes_package_attempt": False,
    "canonical_package_state_effect": "none",
    "sample_source": sample,
}

try:
    os_release = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            os_release[k] = v.strip().strip('"')
    if os_release.get("VERSION_ID") != "26.04":
        raise RuntimeError(f"expected Ubuntu 26.04, got {os_release.get('PRETTY_NAME')}")

    showsrc = run(["apt-cache", "showsrc", sample])
    if not showsrc.strip():
        raise RuntimeError(f"no apt-cache showsrc result for {sample}")
    (OUT / "apt-cache-showsrc.txt").write_text(showsrc)

    versions = []
    for line in showsrc.splitlines():
        if line.startswith("Version: "):
            versions.append(line.split(": ", 1)[1].strip())
    if not versions:
        raise RuntimeError("source reference returned no Version fields")

    with tempfile.TemporaryDirectory(prefix="supralinux-plasma-src-") as td:
        work = Path(td)
        download_log = run(["apt-get", "source", "--download-only", sample], cwd=work)
        (OUT / "apt-get-source.log").write_text(download_log)

        dscs = sorted(work.glob("*.dsc"))
        if len(dscs) != 1:
            raise RuntimeError(f"expected exactly one .dsc, got {len(dscs)}")

        dsc = dscs[0]
        extract = work / "extracted"
        extract_log = run(["dpkg-source", "-x", dsc.name, extract.name], cwd=work)
        (OUT / "dpkg-source-extract.log").write_text(extract_log)

        required = [
            extract / "debian/control",
            extract / "debian/rules",
            extract / "debian/changelog",
        ]
        missing = [str(p.relative_to(extract)) for p in required if not p.is_file()]
        if missing:
            raise RuntimeError("missing packaging files: " + ",".join(missing))

        changelog_source = run(["dpkg-parsechangelog", "-l", str(extract / "debian/changelog"), "-S", "Source"]).strip()
        changelog_version = run(["dpkg-parsechangelog", "-l", str(extract / "debian/changelog"), "-S", "Version"]).strip()
        if changelog_source != sample:
            raise RuntimeError(f"downloaded source mismatch: {changelog_source}")
        if changelog_version not in versions:
            raise RuntimeError(f"downloaded version {changelog_version} absent from apt source records")

        downloaded = {}
        for path in sorted(work.iterdir()):
            if path.is_file():
                downloaded[path.name] = {
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                }

        packaging_archive = OUT / "sample-debian-tree.tar"
        run(["tar", "-cf", str(packaging_archive), "-C", str(extract), "debian"])

        result = dict(base)
        result.update({
            "state": "PASS",
            "ubuntu_version_id": os_release["VERSION_ID"],
            "source_reference_available": True,
            "source_record_versions": versions,
            "materialized_source": changelog_source,
            "materialized_version": changelog_version,
            "dsc_file": dsc.name,
            "dsc_sha256": sha256(dsc),
            "downloaded_files": downloaded,
            "debian_tree_sha256": tree_hash(extract / "debian"),
            "sample_debian_tree_tar_sha256": sha256(packaging_archive),
            "required_packaging_files": "PASS",
            "apt_get_source_download_only": "PASS",
            "dpkg_source_extract": "PASS",
            "next_gate": definition["next_gate_on_pass"],
        })
        write_result(result)
        print(json.dumps(result, indent=2, sort_keys=True))
except Exception as exc:
    result = dict(base)
    result.update({
        "state": "INFRA_INVALID",
        "infrastructure_incident": True,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "next_gate": definition["next_gate_on_failure"],
    })
    write_result(result)
    print(json.dumps(result, indent=2, sort_keys=True), file=sys.stderr)
    raise SystemExit(1)
