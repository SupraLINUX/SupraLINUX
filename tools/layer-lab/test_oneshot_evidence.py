import unittest
from oneshot_evidence import report


class TrialEvidence(unittest.TestCase):
    def test_three_phases(self):
        def log(deployment, phase):
            return "\n".join(["SUPRA_LAYER_UEFI_READY", deployment, phase, "SUPRA_TARGET_BOOT_READY"])
        logs = {"arm": log("SUPRA_LAYER_PREVIOUS_READY", "SUPRA_ONESHOT_ARMED"),
                "trial": log("SUPRA_LAYER_NEW_READY", "SUPRA_ONESHOT_CONSUMED"),
                "return": log("SUPRA_LAYER_PREVIOUS_READY", "SUPRA_ONESHOT_RETURNED")}
        self.assertTrue(report(logs)["default_return_verified"])
        self.assertFalse(report(logs)["automatic_rollback_verified"])
        logs["return"] = logs["arm"]
        with self.assertRaises(ValueError):
            report(logs)
