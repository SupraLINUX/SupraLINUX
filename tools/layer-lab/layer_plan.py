"""D-P1 narrow test fixture plan, not a general dependency resolver."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system-lab"))
from compare_snapshot import compare
from verify_snapshot import candidate
from snapshot_lock import validate_database, lock


def read_package_metadata(archive_path, package):
    found = []
    with tarfile.open(archive_path, "r:*") as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith("/desc"):
                continue
            if member.size > 1024 * 1024:
                raise ValueError("Oversized repository metadata")
            raw = archive.extractfile(member)
            if raw is None:
                raise ValueError("Missing metadata")
            fields = {}
            for block in raw.read().decode("utf-8").strip().split("\n\n"):
                lines = block.splitlines()
                if not lines:
                    continue
                key = lines[0].strip("%")
                if key in fields:
                    raise ValueError("Duplicate field")
                fields[key] = lines[1:]
            if fields.get("NAME") == [package]:
                found.append(fields)
    if len(found) != 1:
        raise ValueError("Expected exactly one layer package record")
    return found[0]


def plan_delta(base, fixture, fields):
    pkg = fixture["package"]
    actual = {p["name"]: p["version"] for p in base["packages"]}
    if len(actual) != len(base["packages"]):
        raise ValueError("Duplicate base package")
    if pkg["name"] in actual:
        raise ValueError("Layer package already present")
    if fields.get("DEPENDS", []) != fixture["depends"] or any(
            dep not in actual for dep in fixture["depends"]):
        raise ValueError("Fixture dependency drift; require actual resolver review")
    if any(fields.get(k) for k in ("CONFLICTS", "REPLACES", "PROVIDES")):
        raise ValueError("Fixture no longer a plain additive package")
    if fields.get("CSIZE") != [str(fixture["compressed_bytes"])] or fields.get("ISIZE") != [str(fixture["installed_bytes"])]:
        raise ValueError("Fixture size drift")
    for key, name in (("NAME", "name"), ("VERSION", "version"), ("ARCH", "arch"),
                      ("FILENAME", "filename"), ("SHA256SUM", "sha256")):
        if fields.get(key) != [pkg[name]]:
            raise ValueError("Fixture identity drift")
    expected = dict(actual)
    expected[pkg["name"]] = pkg["version"]
    return {
        "schema_version": 1, "kind": "experimental-layer-plan",
        "base_lock_sha256": fixture["base_lock_sha256"],
        "snapshot": fixture["snapshot"], "addition": pkg,
        "dependency_versions": {name: actual[name] for name in fixture["depends"]},
        "base_package_count": len(actual), "expected_package_count": len(expected),
        "expected_inventory": expected, "removed": [], "upgraded": [],
        "compressed_bytes": fixture["compressed_bytes"], "installed_bytes": fixture["installed_bytes"],
        "layer_signature_verified": False, "transaction_verified": False,
        "stage_boot_verified": False, "atomic_activation_verified": False,
    }


def main():
    config, fixture_path, evidence, comparison, output = map(Path, sys.argv[1:])
    fixture = json.loads(fixture_path.read_text())
    base = candidate(config, evidence)
    digest = hashlib.sha256((evidence / "snapshot-lock.json").read_bytes()).hexdigest()
    if fixture["schema_version"] != 1 or digest != fixture["base_lock_sha256"] or base["snapshot"] != fixture["snapshot"]:
        raise ValueError("Unexpected base fixture identity")
    verification = json.loads((evidence / "snapshot-verification.json").read_text())
    if compare(base, base, verification, digest) != json.loads((comparison / "resolution-comparison.json").read_text()):
        raise ValueError("Base comparison evidence mismatch")
    pkg = fixture["package"]
    cfg = json.loads(config.read_text())
    cfg["packages"] = [pkg["name"]]
    keys = ("repository", "name", "version", "arch", "sha256", "filename", "url")
    layer_lock = lock(cfg, ["|".join(pkg[k] for k in keys)], base["databases"])
    validate_database(layer_lock, evidence)
    fields = read_package_metadata(evidence / (pkg["repository"] + ".db"), pkg["name"])
    result = plan_delta(base, fixture, fields)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(f"Candidate plan: {result['base_package_count']} -> {result['expected_package_count']} packages; no installation performed")


if __name__ == "__main__":
    main()
