#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT / "scripts/run-kde-tier3-knewstuff-runtime-validation.sh").read_text()
verifier = ROOT / "scripts/verify-kde-runtime-artifact.py"

def run_verifier(path, node, version, result, expect_ok=True):
    p = subprocess.run(
        [sys.executable, str(verifier), str(path), node, version, result],
        text=True, capture_output=True
    )
    if expect_ok and p.returncode != 0:
        raise SystemExit(f"verifier unexpectedly failed: {p.stderr}{p.stdout}")
    if not expect_ok and p.returncode == 0:
        raise SystemExit("verifier unexpectedly accepted invalid fixture")
    return p

with TemporaryDirectory() as td:
    root = Path(td)
    aid = 123456
    label = "synthetic-node"
    version = "6.30.0-0supralinux1"
    extracted = root / f"{aid}-{label}"
    extracted.mkdir()
    sibling_zip = root / f"{aid}-{label}.zip"
    sibling_zip.write_bytes(b"synthetic zip placeholder")

    historical_matches = list(root.glob(f"{aid}-*"))
    if len(historical_matches) != 2:
        raise SystemExit("synthetic preflight failed to reproduce directory+zip ambiguity")

    selected = root / f"{aid}-{label}"
    if not selected.is_dir():
        raise SystemExit("exact artifact-directory selector did not select extracted directory")

    payload = extracted / "synthetic_6.30.0-0supralinux1_amd64.deb"
    payload.write_bytes(b"synthetic retained artifact payload")
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()

    # Generation 1: node-only historical result.json.
    (extracted / "result.json").write_text(json.dumps({"node": label}) + "\n")
    run_verifier(extracted, label, version, "PASS")

    # Generation 2: package_version added, but no result/hash map yet.
    (extracted / "result.json").write_text(json.dumps({
        "node": label, "package_version": version
    }) + "\n")
    run_verifier(extracted, label, version, "PASS")
    run_verifier(extracted, label, version + ".wrong", "PASS", expect_ok=False)

    # Generation 3: PASS result/state exists, still no internal hash map.
    (extracted / "result.json").write_text(json.dumps({
        "node": label,
        "package_version": version,
        "result": "PASS",
        "package_state_effect": "PASS",
    }) + "\n")
    run_verifier(extracted, label, version, "PASS")

    # Generation 4: full internal artifact SHA-256 map.
    (extracted / "result.json").write_text(json.dumps({
        "node": label,
        "package_version": version,
        "result": "PASS",
        "package_state_effect": "PASS",
        "artifacts": {payload.name: digest},
    }) + "\n")
    run_verifier(extracted, label, version, "PASS")

    payload.write_bytes(b"tampered payload")
    run_verifier(extracted, label, version, "PASS", expect_ok=False)

if 'artifact_dir=root/f"{aid}-{label}"' not in runner:
    raise SystemExit("runtime runner does not use the certified exact artifact-directory selector")
if 'root.glob(f"{aid}-*")' in runner:
    raise SystemExit("runtime runner still contains the ambiguous artifact glob")
if "verify-kde-runtime-artifact.py" not in runner:
    raise SystemExit("runtime runner does not invoke the certified result.json verifier")

print("KNewStuff runtime-validation infrastructure preflight: PASS")
print("historical_bug_reproduced=directory-plus-sibling-zip")
print("certified_selector=exact-extracted-directory")
print("schema_generation_legacy_minimal=PASS")
print("schema_generation_version_only=PASS")
print("schema_generation_result_no_hashes=PASS")
print("schema_generation_hash_map=PASS")
print("tamper_rejection=PASS")
