import unittest
from promotion_evidence import report


class PromotionEvidence(unittest.TestCase):
    def test_exact_order_and_persistence(self):
        def log(deployment, *phase):
            return "\n".join(["SUPRA_LAYER_UEFI_READY", deployment, *phase, "SUPRA_TARGET_BOOT_READY"])
        logs = {"arm": log("SUPRA_LAYER_PREVIOUS_READY", "SUPRA_PROMOTION_ARMED"),
                "promote": log("SUPRA_LAYER_NEW_READY", "SUPRA_PROMOTION_COMMITTED"),
                "persist": log("SUPRA_LAYER_NEW_READY", "SUPRA_PROMOTION_PERSISTENT", "SUPRA_PROMOTION_REVERSED"),
                "revert": log("SUPRA_LAYER_PREVIOUS_READY", "SUPRA_PROMOTION_PREVIOUS_READY")}
        result = report(logs)
        self.assertTrue(result["persistent_default_verified"])
        self.assertFalse(result["atomic_activation_verified"])
        logs["persist"] = log("SUPRA_LAYER_NEW_READY", "SUPRA_PROMOTION_REVERSED", "SUPRA_PROMOTION_PERSISTENT")
        with self.assertRaises(ValueError):
            report(logs)
