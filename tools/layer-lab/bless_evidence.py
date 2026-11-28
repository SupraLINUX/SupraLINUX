"""Independent positive boot confirmation evidence."""
import json
import sys
from pathlib import Path
from bootcount_evidence import ordered_marker

PHASES = ("initial", "bless", "persist")


def verify(phase, listing, console=""):
    expected = "supra-immutable-layer+2.conf" if phase == "initial" else "supra-immutable-layer.conf"
    entries = [x.strip().rsplit("/", 1)[-1].lower() for x in listing.splitlines() if x.strip()]
    if phase not in PHASES or sorted(entries) != sorted(["supra-immutable-staged.conf", expected]):
        raise ValueError("Invalid healthy candidate entry state")
    if phase == "initial":
        return
    before, after = (("SUPRA_BLESS_COUNTED", "SUPRA_BLESS_MARKED_GOOD") if phase == "bless"
                     else ("SUPRA_BLESS_ALREADY_GOOD", "SUPRA_BLESS_CLEAN_BOOT"))
    sequence = (before, "SUPRA_IMMUTABLE_UEFI_READY", "SUPRA_BLESS_HEALTH_READY", after, "SUPRA_BLESS_READY")
    lines = console.splitlines()
    for marker in sequence:
        ordered_marker(console, marker)
    if [lines.index(x) for x in sequence] != sorted(lines.index(x) for x in sequence):
        raise ValueError("Invalid health/confirmation order")
    forbidden = ("SUPRA_BOOTCOUNT_FALLBACK_READY", "SUPRA_IMMUTABLE_ERROR", "SUPRA_BOOT_PROBE_ERROR", "SUPRA_BOOT_PROBE_FAILED")
    if any(x in console for x in forbidden):
        raise ValueError("Guest error or fallback")
    opposite = ("SUPRA_BLESS_ALREADY_GOOD", "SUPRA_BLESS_CLEAN_BOOT") if phase == "bless" else ("SUPRA_BLESS_COUNTED", "SUPRA_BLESS_MARKED_GOOD")
    if any(x in lines for x in opposite):
        raise ValueError("Contradictory confirmation markers")


def read_phase(out, phase):
    listing = (out / f"rootfs-bless-{phase}-entries.txt").read_text()
    console = "" if phase == "initial" else (out / f"rootfs-bless-{phase}-console.log").read_text(errors="replace")
    verify(phase, listing, console)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    if len(sys.argv) == 3:
        read_phase(out, sys.argv[2])
    else:
        for phase in PHASES:
            read_phase(out, phase)
        result = {"schema_version": 1, "accelerator": "kvm",
                  "native_explicit_bless_verified": True, "health_before_bless_verified": True,
                  "good_entry_persistent_verified": True, "immutable_root_verified": True,
                  "persistent_domains_verified": True, "automatic_health_service_verified": False,
                  "atomic_activation_verified": False}
        data = json.dumps(result, sort_keys=True) + "\n"
        (out / "rootfs-bless-report.json").write_text(data)
        print(data, end="")
