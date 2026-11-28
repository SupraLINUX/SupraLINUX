import unittest
from auto_bless_evidence import verify


class AutoBlessTests(unittest.TestCase):
    def test_accept_and_reject_require_different_evidence(self):
        accepted = "supra-immutable-staged.conf\nsupra-immutable-layer.conf\n"
        rejected = accepted.replace("layer.conf", "layer+0-1.conf")
        log = ("SUPRA_IMMUTABLE_UEFI_READY\nSUPRA_AUTO_HEALTH_CHECKS_PASSED\n"
               "SUPRA_AUTO_HEALTH_ACCEPTED\nSUPRA_AUTO_BLESS_NATIVE_GOOD\n"
               "SUPRA_AUTO_BLESS_READY\nSUPRA_TARGET_BOOT_READY\n")
        verify("accept", "first", accepted, log)
        with self.assertRaises(ValueError):
            verify("reject", "first", rejected, log)
        reject_log = log.replace("ACCEPTED", "REJECTED").replace("NATIVE_GOOD", "BLOCKED")
        verify("reject", "first", rejected, reject_log)
        with self.assertRaises(ValueError):
            verify("reject", "first", accepted, reject_log)
        verify("reject", "second", rejected, "SUPRA_IMMUTABLE_UEFI_READY\nSUPRA_BOOTCOUNT_FALLBACK_READY\nSUPRA_TARGET_BOOT_READY\n")
