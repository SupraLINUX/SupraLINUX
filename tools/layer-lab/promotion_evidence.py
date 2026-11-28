"""Explicit runtime selection persistence and reversal; not crash consistency."""
import json
from pathlib import Path
import sys
from layer_uefi_evidence import verify


def report(consoles):
    cases = (("arm", "staged", ["SUPRA_PROMOTION_ARMED"]),
             ("promote", "layer", ["SUPRA_PROMOTION_COMMITTED"]),
             ("persist", "layer", ["SUPRA_PROMOTION_PERSISTENT", "SUPRA_PROMOTION_REVERSED"]),
             ("revert", "staged", ["SUPRA_PROMOTION_PREVIOUS_READY"]))
    markers = {m for _, _, seq in cases for m in seq}
    for phase, deployment, expected in cases:
        console = consoles[phase]
        verify(console, deployment)
        lines = console.splitlines()
        if [line for line in lines if line in markers] != expected:
            raise ValueError("Unexpected promotion phase")
        previous = "SUPRA_LAYER_PREVIOUS_READY" if deployment == "staged" else "SUPRA_LAYER_NEW_READY"
        if not lines.index(previous) < lines.index(expected[0]) <= lines.index(expected[-1]) < lines.index("SUPRA_TARGET_BOOT_READY"):
            raise ValueError("Unexpected promotion ordering")
    return {"schema_version": 1, "accelerator": "kvm", "runtime_promotion_verified": True,
            "persistent_default_verified": True, "explicit_reversal_verified": True,
            "atomic_activation_verified": False, "automatic_rollback_verified": False,
            "immutable_active_root_verified": False, "release_signed": False}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    result = report({phase: (out / f"rootfs-layer-promotion-{phase}-console.log").read_text(errors="replace")
                     for phase in ("arm", "promote", "persist", "revert")})
    (out / "rootfs-layer-promotion-report.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
