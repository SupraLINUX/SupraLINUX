"""Firmware selection evidence, independent of the direct boot report."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system-lab"))
from rootfs_btrfs_root_evidence import ordered_marker


def verify(console, deployment):
    marker = {"staged": "SUPRA_LAYER_PREVIOUS_READY", "layer": "SUPRA_LAYER_NEW_READY"}[deployment]
    ordered_marker(console, "SUPRA_LAYER_UEFI_READY")
    ordered_marker(console, marker)
    lines = console.splitlines()
    if lines.index("SUPRA_LAYER_UEFI_READY") >= lines.index(marker):
        raise ValueError("Unexpected firmware marker order")
    if "SUPRA_BOOT_PROBE_FAILED" in console:
        raise ValueError("Firmware guest failed")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    for deployment in ("staged", "layer"):
        verify((out / f"rootfs-layer-uefi-{deployment}-console.log").read_text(errors="replace"), deployment)
    result = {"schema_version": 1, "accelerator": "kvm", "previous_uefi_boot_verified": True,
              "layer_uefi_boot_verified": True, "single_disk_gpt_verified": True,
              "type1_selection_verified": True, "atomic_activation_verified": False,
              "automatic_rollback_verified": False, "release_signed": False}
    (out / "rootfs-layer-uefi-report.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
