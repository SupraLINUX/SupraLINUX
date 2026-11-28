import unittest
from install_interruption_evidence import report


class InstallInterruption(unittest.TestCase):
    def test_reject_published_or_missing_signal(self):
        i = "SUPRA_INSTALL_INTERRUPT_POINT\n"
        r = "SUPRA_INSTALL_RECOVERED\nSUPRA_TARGET_BOOT_READY\n"
        p = "SUPRA_LAYER_PREVIOUS_READY\nSUPRA_TARGET_BOOT_READY\n"
        signal = {"marker": "SUPRA_INSTALL_INTERRUPT_POINT", "returncode": -9, "signal": "SIGKILL"}
        self.assertTrue(report(i, r, p, signal)["previous_boot_verified"])
        with self.assertRaises(ValueError):
            report(i + "SUPRA_LAYER_PREPARED", r, p, signal)
        with self.assertRaises(ValueError):
            report(i, r, p, {})
