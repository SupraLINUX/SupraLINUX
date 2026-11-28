"""Validate independent firmware and systemd readiness evidence."""
import json
from pathlib import Path
import sys

from rootfs_evidence import check_target


def report(console):
    check_target(console)
    lines = console.splitlines()
    if lines.count("SUPRA_UEFI_BOOT_READY") != 1 or (
        lines.index("SUPRA_UEFI_BOOT_READY") >= lines.index("SUPRA_TARGET_BOOT_READY")
    ):
        raise ValueError("Missing or inconsistent EFI readiness")
    return {"schema_version": 1, "uefi_boot_verified": True,
            "accelerator": "kvm", "secure_boot_verified": False,
            "single_disk_image_verified": False, "release_signed": False}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    result = report((out / "rootfs-uefi-console.log").read_text(errors="replace"))
    (out / "rootfs-uefi-boot.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    print("UEFI target boot verified")
