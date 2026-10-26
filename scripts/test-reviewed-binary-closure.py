#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify-reviewed-binary-closure.py"
spec = importlib.util.spec_from_file_location("binary_closure", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    proof_dir = root / "proof"
    proof_dir.mkdir()
    proof = {
        "node": "breeze-icons",
        "state": "PASS",
        "offline_restore_verified": True,
        "source_package": "kf6-breeze-icons",
        "inspection": {
            "binaries": [
                {
                    "package": "libkf6breezeicons6",
                    "version": "4:6.30.0-0supralinux1",
                    "architecture": "amd64",
                    "file": "libkf6breezeicons6_6.30.0-0supralinux1_amd64.deb",
                }
            ]
        },
    }
    proof_path = proof_dir / "verification.json"
    proof_path.write_text(json.dumps(proof))
    support = {
        "nodes": {
            "breeze-icons": {
                "state": "PASS",
                "downstream_eligible": True,
                "evidence": {
                    "path": str(proof_path.relative_to(root)),
                    "sha256": digest(proof_path),
                },
            }
        }
    }
    dag = {
        "nodes": {
            "kiconthemes": {"source_package": "kf6-kiconthemes"},
        }
    }
    packages = """Package: libkf6iconthemes6
Version: 6.30.0-0supralinux3
Architecture: amd64
Source: kf6-kiconthemes
Depends: libc6 (>= 2.38), libkf6breezeicons6 (>= 4:6.30.0~)

"""
    base_record = {
        "source_package": "example",
        "frameworks_predecessors": {
            "kiconthemes": {
                "source_package": "kf6-kiconthemes",
                "version": "6.30.0-0supralinux3",
                "binaries": [
                    {
                        "package": "libkf6iconthemes6",
                        "architecture": "amd64",
                        "sha256": "1" * 64,
                    }
                ],
            }
        },
    }
    campaign = {"nodes": {"example": base_record}}
    result = module.verify(root, campaign, "example", packages, dag, support)
    assert result["state"] == "BLOCKED"
    assert result["package_attempt_consumed"] is False
    assert result["vm_created"] is False
    assert result["missing_local_relations"][0]["providers"][0]["provider_node"] == "breeze-icons"

    fixed = json.loads(json.dumps(campaign))
    fixed["nodes"]["example"]["frameworks_predecessors"]["breeze-icons"] = {
        "source_package": "kf6-breeze-icons",
        "version": "4:6.30.0-0supralinux1",
        "binaries": [
            {
                "package": "libkf6breezeicons6",
                "architecture": "amd64",
                "sha256": "2" * 64,
            }
        ],
    }
    result = module.verify(root, fixed, "example", packages, dag, support)
    assert result["state"] == "PASS"
    assert not result["missing_local_relations"]

    wrong = json.loads(json.dumps(fixed))
    wrong["nodes"]["example"]["frameworks_predecessors"]["breeze-icons"]["version"] = "4:6.29.0-0supralinux1"
    result = module.verify(root, wrong, "example", packages, dag, support)
    assert result["state"] == "BLOCKED"

    parsed = module.parse_relation(
        "liba (>= 1), libb:any | libc (<< 3), libd [amd64]"
    )
    assert [a["name"] for a in parsed[1]["alternatives"]] == ["libb", "libc"]

subprocess.run(["python3", "-m", "py_compile", str(SCRIPT)], check=True)
print("Reviewed binary closure fast rejection tests: PASS")
