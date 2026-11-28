"""Record only the Btrfs fixture facts verified by the guest."""
import json
from pathlib import Path
import sys

from rootfs_evidence import check_target


def report(console):
    check_target(console)
    lines = console.splitlines()
    if lines.count("SUPRA_BTRFS_LAB_READY") != 1 or (
        lines.index("SUPRA_BTRFS_LAB_READY") >= lines.index("SUPRA_TARGET_BOOT_READY")
    ):
        raise ValueError("Btrfs fixture incomplete")
    return {"schema_version": 1, "kind": "btrfs-subvolume-fixture",
            "readonly_base_preserved": True, "staging_isolated": True,
            "persistent_fixture_preserved": True, "rollback_snapshot_verified": True,
            "failed_stage_discarded": True, "remount_verified": True,
            "actual_package_layer_verified": False, "atomic_boot_switch_verified": False,
            "power_cut_verified": False, "btrfs_root_boot_verified": False,
            "release_signed": False}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    result = report((out / "rootfs-btrfs-console.log").read_text(errors="replace"))
    (out / "rootfs-btrfs-report.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
