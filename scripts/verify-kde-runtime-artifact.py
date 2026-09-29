#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import sys

if len(sys.argv) != 5:
    raise SystemExit("usage: verify-kde-runtime-artifact.py <artifact-dir> <expected-node> <expected-version> <expected-result>")

artifact_dir = Path(sys.argv[1])
expected_node, expected_version, expected_result = sys.argv[2:5]
result_path = artifact_dir / "result.json"
if not artifact_dir.is_dir():
    raise SystemExit(f"artifact directory missing: {artifact_dir}")
if not result_path.is_file():
    raise SystemExit(f"result.json missing: {result_path}")

result = json.loads(result_path.read_text())
if result.get("node") != expected_node:
    raise SystemExit(f"{expected_node}: result.json node {result.get('node')!r} does not match")
if result.get("package_version") != expected_version:
    raise SystemExit(f"{expected_node}: result.json package_version {result.get('package_version')!r} != {expected_version!r}")
if result.get("result") != expected_result:
    raise SystemExit(f"{expected_node}: result.json result {result.get('result')!r} != {expected_result!r}")
if expected_result == "RUNTIME_PENDING" and result.get("build_result") != "PASS":
    raise SystemExit(f"{expected_node}: RUNTIME_PENDING artifact lacks build_result=PASS")
if expected_result == "PASS" and result.get("package_state_effect") != "PASS":
    raise SystemExit(f"{expected_node}: PASS artifact lacks package_state_effect=PASS")

artifacts = result.get("artifacts")
if not isinstance(artifacts, dict) or not artifacts:
    raise SystemExit(f"{expected_node}: result.json artifacts map missing or empty")

for name, want in sorted(artifacts.items()):
    if Path(name).name != name:
        raise SystemExit(f"{expected_node}: unsafe/non-flat artifact name in result.json: {name}")
    if not isinstance(want, str) or len(want) != 64:
        raise SystemExit(f"{expected_node}: invalid SHA-256 for {name}")
    path = artifact_dir / name
    if not path.is_file():
        raise SystemExit(f"{expected_node}: result.json artifact missing: {name}")
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != want:
        raise SystemExit(f"{expected_node}: internal artifact hash mismatch for {name}: {got} != {want}")

print(f"{expected_node}: internal result.json identity and artifact hashes PASS")
