"""Evidence adapter for the additive transaction; no activation or release claim."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system-lab"))
from rootfs_btrfs_root_evidence import ordered_marker


def inventory(text):
    result = {}
    for row in text.splitlines():
        name, version = row.split()
        if name in result:
            raise ValueError("Duplicate installed package")
        result[name] = version
    return result


def report(plan, files):
    for label, marker in (("prepare", "SUPRA_LAYER_PREPARED"),
                          ("staged", "SUPRA_LAYER_PREVIOUS_READY"),
                          ("layer", "SUPRA_LAYER_NEW_READY")):
        console = files(label + "-console.log")
        ordered_marker(console, marker)
        if "SUPRA_BOOT_PROBE_FAILED" in console:
            raise ValueError("Failed boot probe")
    expected = plan["expected_inventory"]
    addition = plan["addition"]
    base = dict(expected)
    del base[addition["name"]]
    if len(base) != plan["base_package_count"] or len(expected) != plan["expected_package_count"]:
        raise ValueError("Plan count mismatch")
    for role in ("active", "base", "previous"):
        for phase in ("before", "after"):
            if inventory(files(f"{role}-{phase}.txt")) != base:
                raise ValueError("Prior inventory changed")
    import re
    for role in ("base", "previous"):
        before = files(role + "-before-content.sha256").strip()
        after = files(role + "-after-content.sha256").strip()
        if not re.fullmatch(r"[0-9a-f]{64}  -", before) or before != after:
            raise ValueError("Prior filesystem content changed: " + role)
    if inventory(files("layer-installed.txt")) != expected:
        raise ValueError("Layer inventory mismatch")
    rows = files("signature.tsv").splitlines()
    if len(rows) != 1:
        raise ValueError("Missing unique signature evidence")
    name, digest, signer = rows[0].split("\t")
    if name != addition["name"] or digest != addition["sha256"] or len(signer) not in (40, 64) or any(c not in "0123456789ABCDEF" for c in signer):
        raise ValueError("Layer signature evidence mismatch")
    if not files("tree-version.txt").strip():
        raise ValueError("Missing executable evidence")
    return {"schema_version": 1, "accelerator": "kvm",
            "base_package_count": len(base), "layer_package_count": len(expected),
            "layer_signature_verified": True, "transaction_verified": True,
            "prior_inventory_preserved": True, "prior_content_digest_preserved": True, "previous_boot_verified": True,
            "stage_boot_verified": True, "direct_kernel_boot_verified": True,
            "atomic_activation_verified": False, "immutable_active_root_verified": False,
            "layer_uefi_boot_verified": False, "release_signed": False}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    plan = json.loads((out / "rootfs-layer-plan.json").read_text())
    result = report(plan, lambda name: (out / ("rootfs-layer-" + name)).read_text(errors="replace"))
    (out / "rootfs-layer-report.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
