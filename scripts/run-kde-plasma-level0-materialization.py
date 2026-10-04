#!/usr/bin/env python3
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
LEVEL0 = json.loads((ROOT / "manifests/kde-plasma-level0.json").read_text())
OUT = ROOT / "evidence/kde-plasma-level0-materialization"
WORK = ROOT / ".work/kde-plasma-level0-materialization"
RESULT = OUT / "result.json"
EXPECTED_FPR = "0AAC775BB6437A8D9AF7A3ACFE0784117FBCE11D"
KEY = ROOT / "packages/kde/karchive/debian/upstream/signing-key.asc"
MAX_WORKERS = 6

class ReviewRequired(Exception):
    pass

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run(cmd, cwd=None, log=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=600)
    if log is not None:
        Path(log).write_text(p.stdout, encoding="utf-8")
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout[-4000:]}")
    return p

def source_versions(text):
    return sorted(set(re.findall(r"^Version:\s*(\S+)\s*$", text, flags=re.M)))

def semantic_plasma6(version):
    return re.match(r"^(?:\d+:)?6\.", version) is not None

def valid_release_signature(status, primary_fingerprint=EXPECTED_FPR):
    for line in status.splitlines():
        fields = line.split()
        if len(fields) >= 11 and fields[:2] == ["[GNUPG:]", "VALIDSIG"]:
            if fields[2] == primary_fingerprint or fields[-1] == primary_fingerprint:
                return True
    return False

def make_debian_tar(src, dst):
    run([
        "tar", "--sort=name", "--mtime=@0", "--owner=0", "--group=0", "--numeric-owner",
        "-cf", str(dst), "-C", str(src.parent), src.name
    ])

def materialize(node_id):
    node = LEVEL0["nodes"][node_id]
    ref_source = node["packaging_reference"]["source_package"]
    node_out = OUT / "nodes" / node_id
    upstream_out = OUT / "upstream" / node_id
    node_work = WORK / node_id
    shutil.rmtree(node_work, ignore_errors=True)
    node_work.mkdir(parents=True)
    node_out.mkdir(parents=True, exist_ok=True)
    upstream_out.mkdir(parents=True, exist_ok=True)

    metadata = {
        "node": node_id,
        "state": "PENDING",
        "package_execution_started": False,
        "consumes_package_attempt": False,
        "canonical_package_state_effect": "none",
        "upstream": {
            "version": node["upstream_version"],
            "url": node["upstream_source_url"],
            "expected_sha256": node["upstream_source_sha256"],
        },
        "ubuntu_reference": {"source_package": ref_source},
    }
    try:
        showsrc = run(["apt-cache", "showsrc", ref_source], cwd=node_work)
        (node_out / "apt-cache-showsrc.txt").write_text(showsrc.stdout, encoding="utf-8")
        versions = source_versions(showsrc.stdout)
        if not versions:
            raise ReviewRequired(f"{node_id}: no Ubuntu source record for {ref_source}")

        run(["apt-get", "source", "--download-only", ref_source], cwd=node_work, log=node_out / "apt-get-source.log")
        dscs = sorted(node_work.glob("*.dsc"))
        if len(dscs) != 1:
            raise RuntimeError(f"{node_id}: expected exactly one .dsc, got {len(dscs)}")
        dsc = dscs[0]
        extracted = node_work / "extracted"
        run(["dpkg-source", "-x", dsc.name, extracted.name], cwd=node_work, log=node_out / "dpkg-source-extract.log")
        for rel in ("debian/control", "debian/rules", "debian/changelog"):
            if not (extracted / rel).is_file():
                raise ReviewRequired(f"{node_id}: required packaging file missing: {rel}")

        src_name = run(["dpkg-parsechangelog", "-l", str(extracted / "debian/changelog"), "-S", "Source"]).stdout.strip()
        src_version = run(["dpkg-parsechangelog", "-l", str(extracted / "debian/changelog"), "-S", "Version"]).stdout.strip()
        if src_name != ref_source:
            raise ReviewRequired(f"{node_id}: extracted Source={src_name}, expected {ref_source}")
        if src_version not in versions:
            raise ReviewRequired(f"{node_id}: selected version {src_version} absent from apt source records")
        if not semantic_plasma6(src_version):
            raise ReviewRequired(f"{node_id}: Ubuntu reference version is not KDE Plasma 6.x: {src_version}")

        deb_tar = node_out / "ubuntu-debian-tree.tar"
        make_debian_tar(extracted / "debian", deb_tar)

        tar_url = node["upstream_source_url"]
        tar_name = Path(urlparse(tar_url).path).name
        tar_path = upstream_out / tar_name
        sig_path = upstream_out / f"{tar_name}.sig"
        run(["curl", "--fail", "--location", "--connect-timeout", "20", "--max-time", "180",
             "--retry", "3", "--retry-delay", "2", "-o", str(tar_path), tar_url],
            log=node_out / "kde-source-download.log")
        actual = sha256(tar_path)
        if actual != node["upstream_source_sha256"]:
            raise ReviewRequired(f"{node_id}: KDE source SHA-256 mismatch")

        run(["curl", "--fail", "--location", "--connect-timeout", "20", "--max-time", "180",
             "--retry", "3", "--retry-delay", "2", "-o", str(sig_path), f"{tar_url}.sig"],
            log=node_out / "kde-signature-download.log")
        verify = run(["gpgv", "--status-fd", "1", "--keyring", str(WORK / "kde-release-keyring.gpg"),
                      str(sig_path), str(tar_path)], check=False)
        (node_out / "gpgv-status.txt").write_text(verify.stdout, encoding="utf-8")
        if verify.returncode != 0 or not valid_release_signature(verify.stdout):
            raise ReviewRequired(f"{node_id}: KDE detached signature did not validate against expected fingerprint")

        downloaded = {}
        for path in sorted(node_work.iterdir()):
            if path.is_file():
                downloaded[path.name] = {"sha256": sha256(path), "size": path.stat().st_size}

        metadata.update({
            "state": "PASS",
            "ubuntu_reference": {
                "source_package": ref_source,
                "source_version": src_version,
                "apt_source_versions": versions,
                "dsc_file": dsc.name,
                "dsc_sha256": sha256(dsc),
                "downloaded_source_files": downloaded,
                "debian_tree_tar_sha256": sha256(deb_tar),
            },
            "upstream": {
                "version": node["upstream_version"],
                "url": tar_url,
                "tarball": tar_name,
                "sha256": actual,
                "signature": sig_path.name,
                "signature_sha256": sha256(sig_path),
                "required_primary_fingerprint": EXPECTED_FPR,
                "signature_verification": "PASS",
            },
        })
    except ReviewRequired as exc:
        metadata["state"] = "REVIEW_REQUIRED"
        metadata["error"] = str(exc)
    except Exception as exc:
        metadata["state"] = "INFRA_INVALID"
        metadata["error"] = str(exc)

    (node_out / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.rmtree(node_work, ignore_errors=True)
    return metadata

def main():
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.rmtree(WORK, ignore_errors=True)
    OUT.mkdir(parents=True)
    WORK.mkdir(parents=True)

    if not KEY.is_file():
        raise SystemExit(f"missing KDE signing key: {KEY}")
    key_info = run(["gpg", "--show-keys", "--with-colons", str(KEY)]).stdout
    fprs = [line.split(":")[9].upper() for line in key_info.splitlines() if line.startswith("fpr:")]
    if EXPECTED_FPR not in fprs:
        raise SystemExit(f"KDE signing key does not contain expected fingerprint {EXPECTED_FPR}")
    run(["gpg", "--batch", "--yes", "--dearmor", "--output", str(WORK / "kde-release-keyring.gpg"), str(KEY)])

    selected = LEVEL0["selected_nodes"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(selected))) as pool:
        future_map = {pool.submit(materialize, node): node for node in selected}
        results = []
        for future in concurrent.futures.as_completed(future_map):
            results.append(future.result())

    results.sort(key=lambda item: selected.index(item["node"]))
    counts = {
        "PASS": sum(r["state"] == "PASS" for r in results),
        "REVIEW_REQUIRED": sum(r["state"] == "REVIEW_REQUIRED" for r in results),
        "INFRA_INVALID": sum(r["state"] == "INFRA_INVALID" for r in results),
    }
    if counts["INFRA_INVALID"]:
        state = "INFRA_INVALID"
    elif counts["REVIEW_REQUIRED"]:
        state = "REVIEW_REQUIRED"
    else:
        state = "PASS"

    result = {
        "schema": 1,
        "node": "plasma-level0-materialization",
        "state": state,
        "run_kind": "planning-materialization",
        "authoritative_package_build": False,
        "selected_node_count": len(selected),
        "counts": counts,
        "nodes": results,
        "inputs_sha256": {
            "level0_manifest": sha256(ROOT / "manifests/kde-plasma-level0.json"),
            "materialization_script": sha256(Path(__file__)),
            "release_signing_key": sha256(KEY),
        },
        "github": {
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
            "source_commit": os.environ.get("SUPRALINUX_SOURCE_COMMIT"),
        },
        "package_execution_started": False,
        "package_attempted": False,
        "consumes_package_attempt": False,
        "canonical_package_state_effect": "none",
        "next_gate": "plasma-level0-candidate-version-assignment" if state == "PASS" else "plasma-level0-materialization-review",
    }
    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result_json_sha256={sha256(RESULT)}", flush=True)
    print("SUPRALINUX_RESULT_JSON_BEGIN", flush=True)
    print(RESULT.read_text(), end="", flush=True)
    print("SUPRALINUX_RESULT_JSON_END", flush=True)

    if state != "PASS":
        for item in results:
            if item["state"] != "PASS":
                print(f"{item['state']}: {item['node']}: {item.get('error','')}", file=sys.stderr)
        raise SystemExit(1)

    print("KDE Plasma Level 0 materialization: PASS")
    print(f"nodes={len(selected)} upstream_sources={counts['PASS']} ubuntu_packaging_trees={counts['PASS']}")
    print("package_execution_started=false consumes_package_attempt=false")

if __name__ == "__main__":
    main()
