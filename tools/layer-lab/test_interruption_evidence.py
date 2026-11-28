import io
import sys
import unittest
from interrupt_vm import interrupt
from interruption_evidence import report


class InterruptionEvidence(unittest.TestCase):
    def test_real_child_kill_and_missing_marker(self):
        result = interrupt([sys.executable, "-u", "-c",
            "import time; print('SUPRA_TRIAL_INTERRUPT_POINT'); time.sleep(30)"], io.BytesIO(), timeout=5)
        self.assertEqual(result["returncode"], -9)
        with self.assertRaises(RuntimeError):
            interrupt([sys.executable, "-c", "print('wrong')"], io.BytesIO(), timeout=5)

    def test_fail_closed(self):
        def previous(marker):
            return "\n".join(["SUPRA_LAYER_UEFI_READY", "SUPRA_LAYER_PREVIOUS_READY", marker, "SUPRA_TARGET_BOOT_READY"])
        arm = previous("SUPRA_ONESHOT_ARMED")
        trial = "SUPRA_LAYER_UEFI_READY\nSUPRA_TRIAL_INTERRUPT_POINT\n"
        returned = previous("SUPRA_ONESHOT_RETURNED")
        injection = {"marker": "SUPRA_TRIAL_INTERRUPT_POINT", "signal": "SIGKILL", "returncode": -9}
        self.assertTrue(report(arm, trial, returned, injection)["previous_default_recovered_verified"])
        with self.assertRaises(ValueError):
            report(arm, trial + "SUPRA_TARGET_BOOT_READY", returned, injection)
        with self.assertRaises(ValueError):
            report(arm, trial, returned, {})
