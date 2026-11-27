"""Evidence for the experimental direct Btrfs-root boot; no UEFI/rollback claim."""
import json
from pathlib import Path
import sys

from rootfs_evidence import check_target


def ordered_marker(console, marker):
    check_target(console)
    lines = console.splitlines()
    if lines.count(marker) != 1 or lines.index(marker) >= lines.index("SUPRA_TARGET_BOOT_READY"):
        raise ValueError("Missing or inconsistent marker: " + marker)


def report(prepare, boot):
    ordered_marker(prepare, "SUPRA_BTRFS_ROOT_PREPARED")
    ordered_marker(boot, "SUPRA_BTRFS_ROOT_READY")
    return {"schema_version": 1, "btrfs_root_boot_verified": True,
            "direct_kernel_boot_verified": True, "accelerator": "kvm",
            "single_disk_uefi_verified": False, "atomic_boot_switch_verified": False,
            "release_signed": False}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    result = report((out / "rootfs-btrfs-root-prepare-console.log").read_text(errors="replace"),
                    (out / "rootfs-btrfs-root-console.log").read_text(errors="replace"))
    (out / "rootfs-btrfs-root-report.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
