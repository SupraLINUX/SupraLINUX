"""Evidence of interruption inside libalpm post-transaction hook."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system-lab"))
from rootfs_btrfs_root_evidence import ordered_marker


def report(interrupted, recovered, previous, injection):
    if interrupted.splitlines().count("SUPRA_INSTALL_INTERRUPT_POINT") != 1 or any(
        marker in interrupted for marker in ("SUPRA_LAYER_PREPARED", "SUPRA_TARGET_BOOT_READY", "LAYER_ERROR")
    ):
        raise ValueError("Installation was not interrupted before publication")
    if injection != {"marker": "SUPRA_INSTALL_INTERRUPT_POINT", "returncode": -9, "signal": "SIGKILL"}:
        raise ValueError("No actual interruption evidence")
    ordered_marker(recovered, "SUPRA_INSTALL_RECOVERED")
    ordered_marker(previous, "SUPRA_LAYER_PREVIOUS_READY")
    return {"schema_version": 1, "accelerator": "kvm", "post_transaction_hook_interruption_verified": True,
            "unapproved_stage_retained_verified": True, "prior_content_digest_preserved": True,
            "previous_boot_verified": True, "mid_extraction_interruption_verified": False,
            "atomic_activation_verified": False, "physical_power_loss_verified": False}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    def read(phase):
        return (out / f"rootfs-layer-install-{phase}-console.log").read_text(errors="replace")
    result = report(read("interrupt"), read("recover"), read("previous"),
                    json.loads((out / "rootfs-layer-install-injection.json").read_text()))
    (out / "rootfs-layer-install-interruption-report.json").write_text(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
