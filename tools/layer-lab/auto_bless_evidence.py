"""Positive and negative automatic health dependency gates."""
import json
import sys
from pathlib import Path
from bootcount_evidence import ordered_marker

PHASES = ("initial", "first", "second")


def verify(mode, phase, listing, console=""):
    expected = {
        "accept": ("supra-immutable-layer+2.conf", "supra-immutable-layer.conf", "supra-immutable-layer.conf"),
        "reject": ("supra-immutable-layer+1.conf", "supra-immutable-layer+0-1.conf", "supra-immutable-layer+0-1.conf"),
    }[mode][PHASES.index(phase)]
    entries = sorted(x.strip().rsplit("/", 1)[-1].lower() for x in listing.splitlines() if x.strip())
    if entries != sorted(["supra-immutable-staged.conf", expected]):
        raise ValueError("Unexpected entry state")
    if phase == "initial":
        return
    if any(x in console for x in ("SUPRA_IMMUTABLE_ERROR", "SUPRA_BOOT_PROBE_ERROR", "SUPRA_BOOT_PROBE_FAILED")):
        raise ValueError("Guest probe failed")
    if mode == "reject" and phase == "second":
        sequence = ("SUPRA_IMMUTABLE_UEFI_READY", "SUPRA_BOOTCOUNT_FALLBACK_READY")
    else:
        decision = "SUPRA_AUTO_HEALTH_ACCEPTED" if mode == "accept" else "SUPRA_AUTO_HEALTH_REJECTED"
        outcome = ("SUPRA_AUTO_BLESS_NATIVE_GOOD" if phase == "first" else "SUPRA_AUTO_BLESS_PERSISTED") if mode == "accept" else "SUPRA_AUTO_BLESS_BLOCKED"
        status = ("dirty" if mode == "reject" else ("indeterminate" if phase == "first" else "clean"))
        sequence = ("SUPRA_IMMUTABLE_UEFI_READY", f"SUPRA_AUTO_HEALTH_STATUS={status}", "SUPRA_AUTO_HEALTH_CHECKS_PASSED", decision)
        if mode == "reject":
            sequence += ("SUPRA_AUTO_OBSERVER_STATUS=dirty",)
        sequence += (outcome, "SUPRA_AUTO_BLESS_READY")
    lines = console.splitlines()
    for marker in sequence:
        ordered_marker(console, marker)
    if [lines.index(x) for x in sequence] != sorted(lines.index(x) for x in sequence):
        raise ValueError("Incorrect automatic health sequence")
    if mode == "reject" and any(x in lines for x in ("SUPRA_AUTO_HEALTH_ACCEPTED", "SUPRA_AUTO_BLESS_NATIVE_GOOD", "SUPRA_AUTO_BLESS_PERSISTED")):
        raise ValueError("Rejected candidate was blessed")
    if mode == "accept" and any(x in lines for x in ("SUPRA_AUTO_HEALTH_REJECTED", "SUPRA_AUTO_BLESS_BLOCKED", "SUPRA_BOOTCOUNT_FALLBACK_READY")):
        raise ValueError("Accepted candidate rejected")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    mode = sys.argv[2]
    def read(phase):
        prefix = out / f"rootfs-auto-{mode}-{phase}"
        listing = Path(f"{prefix}-entries.txt").read_text()
        console = "" if phase == "initial" else Path(f"{prefix}-console.log").read_text(errors="replace")
        verify(mode, phase, listing, console)
    if len(sys.argv) == 4:
        read(sys.argv[3])
    else:
        for phase in PHASES:
            read(phase)
        result = {"schema_version": 1, "mode": mode, "accelerator": "kvm",
                  "native_automatic_health_service_verified": True,
                  "accepted_candidate_persisted_verified": mode == "accept",
                  "rejected_candidate_fallback_verified": mode == "reject",
                  "production_health_policy_verified": False, "atomic_activation_verified": False}
        data = json.dumps(result, sort_keys=True) + "\n"
        (out / f"rootfs-auto-{mode}-report.json").write_text(data)
        print(data, end="")
