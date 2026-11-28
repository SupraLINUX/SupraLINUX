"""Evidence for the separate read-only deployment/persistent-state lab."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system-lab"))
from rootfs_btrfs_root_evidence import ordered_marker


PHASE_MARKERS = {
    "prepare": "SUPRA_IMMUTABLE_PREPARED",
    "first": "SUPRA_IMMUTABLE_FIRST_READY",
    "next": "SUPRA_IMMUTABLE_NEXT_READY",
    "return": "SUPRA_IMMUTABLE_RETURN_READY",
}


def validate_phase(phase, log):
    marker = PHASE_MARKERS[phase]
    ordered_marker(log, marker)
    if any(bad in log for bad in ("SUPRA_BOOT_PROBE_ERROR", "SUPRA_BOOT_PROBE_FAILED")):
        raise ValueError(f"Invalid immutable boot evidence: {phase}")


def report(logs):
    for phase in PHASE_MARKERS:
        validate_phase(phase, logs[phase])
    return {
        "schema_version": 1, "accelerator": "kvm",
        "readonly_deployment_boot_verified": True,
        "persistent_domains_across_deployments_verified": True,
        "ephemeral_run_and_tmp_verified": True,
        "separate_state_disk": True,
        "uefi_immutable_boot_verified": False,
        "atomic_activation_verified": False,
        "production_layout_verified": False,
    }


if __name__ == "__main__":
    out = Path(sys.argv[1])
    if len(sys.argv) == 3:
        phase = sys.argv[2]
        validate_phase(phase, (out / f"rootfs-immutable-{phase}-console.log").read_text(errors="replace"))
        print(f"Validated immutable phase: {phase}")
        sys.exit(0)
    logs = {p: (out / f"rootfs-immutable-{p}-console.log").read_text(errors="replace")
            for p in ("prepare", "first", "next", "return")}
    result = json.dumps(report(logs), sort_keys=True) + "\n"
    (out / "rootfs-immutable-report.json").write_text(result)
    print(result, end="")
