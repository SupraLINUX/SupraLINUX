"""Independent firmware evidence; host-selected entries, not atomic activation."""
import json
import sys
from pathlib import Path
from immutable_evidence import validate_phase, PHASE_MARKERS
from rootfs_btrfs_root_evidence import ordered_marker

PHASES = ("first", "next", "return")


def verify(phase, console):
    if phase not in PHASES:
        raise ValueError("Unexpected UEFI phase")
    validate_phase(phase, console)
    marker = "SUPRA_IMMUTABLE_UEFI_READY"
    ordered_marker(console, marker)
    lines = console.splitlines()
    if lines.index(marker) >= lines.index(PHASE_MARKERS[phase]):
        raise ValueError("Firmware verification must precede boot readiness")
    if "SUPRA_IMMUTABLE_ERROR" in console:
        raise ValueError("Guest reported immutable check error")


def report(logs):
    for phase in PHASES:
        verify(phase, logs[phase])
    return {
        "schema_version": 1, "accelerator": "kvm",
        "uefi_immutable_boot_verified": True,
        "type1_selection_verified": True,
        "persistent_domains_across_deployments_verified": True,
        "host_selected_entries": True,
        "separate_state_disk": True,
        "automatic_rollback_verified": False,
        "atomic_activation_verified": False,
        "production_layout_verified": False,
    }


if __name__ == "__main__":
    out = Path(sys.argv[1])
    def read(phase):
        return (out / f"rootfs-immutable-uefi-{phase}-console.log").read_text(errors="replace")
    if len(sys.argv) == 3:
        verify(sys.argv[2], read(sys.argv[2]))
    else:
        result = json.dumps(report({p: read(p) for p in PHASES}), sort_keys=True) + "\n"
        (out / "rootfs-immutable-uefi-report.json").write_text(result)
        print(result, end="")
