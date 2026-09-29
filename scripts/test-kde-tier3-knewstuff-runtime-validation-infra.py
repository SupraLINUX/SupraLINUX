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
    (extracted / "result.json").write_text(json.dumps({
        "node": label,
        "package_version": version,
        "result": "PASS",
        "package_state_effect": "PASS",
        "artifacts": {payload.name: digest},
    }) + "\n")

    subprocess.run([sys.executable, str(verifier), str(extracted), label, version, "PASS"], check=True)

    payload.write_bytes(b"tampered payload")
    tampered = subprocess.run(
        [sys.executable, str(verifier), str(extracted), label, version, "PASS"],
        text=True, capture_output=True
    )
    if tampered.returncode == 0:
        raise SystemExit("internal-hash verifier accepted a tampered payload")

if 'artifact_dir=root/f"{aid}-{label}"' not in runner:
    raise SystemExit("runtime runner does not use the certified exact artifact-directory selector")
if 'root.glob(f"{aid}-*")' in runner:
    raise SystemExit("runtime runner still contains the ambiguous artifact glob")
if "verify-kde-runtime-artifact.py" not in runner:
    raise SystemExit("runtime runner does not invoke the certified internal-hash verifier")

print("KNewStuff runtime-validation infrastructure preflight: PASS")
print("historical_bug_reproduced=directory-plus-sibling-zip")
print("certified_selector=exact-extracted-directory")
print("internal_result_json_hash_verifier=PASS")
print("tamper_rejection=PASS")
