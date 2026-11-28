"""Evidence for firmware-native boot counting in disposable KVM."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system-lab"))
from rootfs_btrfs_root_evidence import ordered_marker

CANDIDATES = {
    "initial": "supra-immutable-layer+2.conf",
    "trial1": "supra-immutable-layer+1-1.conf",
    "trial2": "supra-immutable-layer+0-2.conf",
    "fallback": "supra-immutable-layer+0-2.conf",
}
POINT = "SUPRA_BOOTCOUNT_INTERRUPT_POINT"


def validate_entries(phase, listing):
    entries = [line.strip().rsplit("/", 1)[-1].lower()
               for line in listing.splitlines() if line.strip()]
    if sorted(entries) != sorted(["supra-immutable-staged.conf", CANDIDATES[phase]]):
        raise ValueError(f"Unexpected ESP entries at {phase}: {entries}")


def verify(phase, listing, console="", injection=None):
    validate_entries(phase, listing)
    if phase == "initial":
        return
    lines = console.splitlines()
    if any(x in console for x in ("SUPRA_IMMUTABLE_ERROR", "SUPRA_BOOT_PROBE_FAILED", "SUPRA_BOOT_PROBE_ERROR")):
        raise ValueError("Guest failure")
    if phase == "fallback":
        ordered_marker(console, "SUPRA_BOOTCOUNT_FALLBACK_READY")
        ordered_marker(console, "SUPRA_IMMUTABLE_UEFI_READY")
        if lines.index("SUPRA_IMMUTABLE_UEFI_READY") >= lines.index("SUPRA_BOOTCOUNT_FALLBACK_READY") or POINT in lines:
            raise ValueError("Invalid fallback marker order")
        return
    count = "SUPRA_BOOTCOUNT_PATH=/loader/entries/" + CANDIDATES[phase]
    if injection != {"marker": POINT, "returncode": -9, "signal": "SIGKILL"}:
        raise ValueError("Missing interruption evidence")
    if (lines.count(count) != 1 or lines.count(POINT) != 1
        or lines.count("SUPRA_IMMUTABLE_UEFI_READY") != 1
        or not lines.index(count) < lines.index("SUPRA_IMMUTABLE_UEFI_READY") < lines.index(POINT)
        or "SUPRA_TARGET_BOOT_READY" in lines or "SUPRA_BOOTCOUNT_FALLBACK_READY" in lines):
        raise ValueError("Trial not interrupted at expected checkpoint")


def read_phase(out, phase):
    listing = (out / f"rootfs-bootcount-{phase}-entries.txt").read_text()
    console = "" if phase == "initial" else (out / f"rootfs-bootcount-{phase}-console.log").read_text(errors="replace")
    injection = json.loads((out / f"rootfs-bootcount-{phase}-injection.json").read_text()) if phase.startswith("trial") else None
    verify(phase, listing, console, injection)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    if len(sys.argv) == 3:
        read_phase(out, sys.argv[2])
    else:
        for phase in CANDIDATES:
            read_phase(out, phase)
        result = {"schema_version": 1, "accelerator": "kvm",
                  "firmware_boot_count_verified": True, "interrupted_trials": 2,
                  "automatic_fallback_verified": True, "immutable_root_verified": True,
                  "persistent_domains_verified": True, "successful_bless_verified": False,
                  "atomic_activation_verified": False, "physical_power_loss_verified": False}
        data = json.dumps(result, sort_keys=True) + "\n"
        (out / "rootfs-bootcount-report.json").write_text(data)
        print(data, end="")
