"""Evidence for the single GPT disk UEFI Btrfs root boot."""
import json
from pathlib import Path
import sys

from rootfs_evidence import check_target

MARKERS = ("SUPRA_BTRFS_ROOT_READY", "SUPRA_UEFI_BOOT_READY",
           "SUPRA_BTRFS_GPT_READY", "SUPRA_TARGET_BOOT_READY")


def report(console):
    check_target(console)
    lines = console.splitlines()
    if any(lines.count(marker) != 1 for marker in MARKERS):
        raise ValueError("Missing or duplicate GPT boot readiness marker")
    positions = [lines.index(marker) for marker in MARKERS]
    if positions != sorted(positions):
        raise ValueError("Out-of-order GPT boot markers")
    if any(line.startswith("SUPRA_BOOT_PROBE_FAILED") for line in lines):
        raise ValueError("Guest probe failed")
    return {"schema_version": 1, "accelerator": "kvm",
            "single_disk_uefi_verified": True, "btrfs_root_boot_verified": True,
            "secure_boot_verified": False, "atomic_boot_switch_verified": False,
            "release_signed": False}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    result = report((out / "rootfs-btrfs-gpt-console.log").read_text(errors="replace"))
    (out / "rootfs-btrfs-gpt-report.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
