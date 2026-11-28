"""Evidence of runtime trial selection, NOT promotion or boot-count recovery."""
import json
from pathlib import Path
import sys

from layer_uefi_evidence import verify


def report(consoles):
    cases = (("arm", "staged", "SUPRA_ONESHOT_ARMED"),
             ("trial", "layer", "SUPRA_ONESHOT_CONSUMED"),
             ("return", "staged", "SUPRA_ONESHOT_RETURNED"))
    markers = {row[2] for row in cases}
    for phase, deployment, marker in cases:
        console = consoles[phase]
        verify(console, deployment)
        lines = console.splitlines()
        if [line for line in lines if line in markers] != [marker]:
            raise ValueError("Unexpected one-shot phase")
        previous = "SUPRA_LAYER_PREVIOUS_READY" if deployment == "staged" else "SUPRA_LAYER_NEW_READY"
        if not lines.index(previous) < lines.index(marker) < lines.index("SUPRA_TARGET_BOOT_READY"):
            raise ValueError("Unexpected one-shot ordering")
    return {"schema_version": 1, "runtime_oneshot_verified": True,
            "trial_consumption_verified": True, "default_return_verified": True,
            "persistent_ovmf_variables_verified": True, "accelerator": "kvm",
            "atomic_activation_verified": False, "automatic_rollback_verified": False,
            "immutable_active_root_verified": False, "release_signed": False}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    result = report({phase: (out / f"rootfs-layer-oneshot-{phase}-console.log").read_text(errors="replace")
                     for phase in ("arm", "trial", "return")})
    (out / "rootfs-layer-oneshot-report.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
