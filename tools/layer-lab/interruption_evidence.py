"""Validate return after actual host interruption, not a clean trial shutdown."""
import json
from pathlib import Path
import sys
from layer_uefi_evidence import verify


def report(arm, trial, returned, injection):
    verify(arm, "staged")
    verify(returned, "staged")
    for console, marker in ((arm, "SUPRA_ONESHOT_ARMED"), (returned, "SUPRA_ONESHOT_RETURNED")):
        lines = console.splitlines()
        if lines.count(marker) != 1 or not lines.index("SUPRA_LAYER_PREVIOUS_READY") < lines.index(marker) < lines.index("SUPRA_TARGET_BOOT_READY"):
            raise ValueError("Unexpected previous deployment phase")
    lines = trial.splitlines()
    if lines.count("SUPRA_TRIAL_INTERRUPT_POINT") != 1 or lines.count("SUPRA_LAYER_UEFI_READY") != 1:
        raise ValueError("Missing unique interruption checkpoint")
    if lines.index("SUPRA_LAYER_UEFI_READY") >= lines.index("SUPRA_TRIAL_INTERRUPT_POINT"):
        raise ValueError("Unexpected interruption ordering")
    if any(m in trial for m in ("SUPRA_LAYER_NEW_READY", "SUPRA_TARGET_BOOT_READY", "SUPRA_BOOT_PROBE_FAILED", "SUPRA_BOOT_PROBE_ERROR")):
        raise ValueError("Trial was not interrupted before readiness")
    if injection != {"marker": "SUPRA_TRIAL_INTERRUPT_POINT", "signal": "SIGKILL", "returncode": -9}:
        raise ValueError("Missing actual process-kill evidence")
    return {"schema_version": 1, "accelerator": "kvm",
            "unpromoted_trial_interruption_verified": True,
            "previous_default_recovered_verified": True,
            "persistent_overlay_reused": True, "atomic_activation_verified": False,
            "automatic_boot_count_rollback_verified": False,
            "immutable_active_root_verified": False, "physical_power_loss_verified": False,
            "release_signed": False}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    def read(phase):
        return (out / f"rootfs-layer-interruption-{phase}-console.log").read_text(errors="replace")
    result = report(read("arm"), read("interrupt"), read("return"),
                    json.loads((out / "rootfs-layer-interruption-injection.json").read_text()))
    (out / "rootfs-layer-interruption-report.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
