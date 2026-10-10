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

# Node identity is present across every retained schema generation.
if result.get("node") != expected_node:
    raise SystemExit(f"{expected_node}: result.json node {result.get('node')!r} does not match")

# Historical artifacts predate package_version/result/artifacts. When a field is
# present, enforce it strictly. Exact package version/binary-set proof is always
# performed separately from the .deb payloads by the runtime runner.
recorded_version = result.get("package_version")
if recorded_version is not None and recorded_version != expected_version:
    raise SystemExit(f"{expected_node}: result.json package_version {recorded_version!r} != {expected_version!r}")

recorded_result = result.get("result")
if recorded_result is not None and recorded_result != expected_result:
    raise SystemExit(f"{expected_node}: result.json result {recorded_result!r} != {expected_result!r}")

if recorded_result == "RUNTIME_PENDING" and result.get("build_result") != "PASS":
    raise SystemExit(f"{expected_node}: RUNTIME_PENDING artifact lacks build_result=PASS")
if recorded_result == "PASS" and "package_state_effect" in result and result.get("package_state_effect") != "PASS":
    raise SystemExit(f"{expected_node}: PASS artifact has non-PASS package_state_effect")

artifacts = result.get("artifacts")
verified_hashes = 0
if artifacts is not None:
    if not isinstance(artifacts, dict) or not artifacts:
        raise SystemExit(f"{expected_node}: result.json artifacts exists but is not a non-empty map")
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
        verified_hashes += 1

schema_class = (
    "hash-map" if artifacts is not None
    else "result-no-hashes" if recorded_result is not None
    else "version-no-result-hashes" if recorded_version is not None
    else "legacy-minimal"
)
print(
    f"{expected_node}: result.json identity PASS "
    f"schema={schema_class} internal_hashes_verified={verified_hashes}"
)
