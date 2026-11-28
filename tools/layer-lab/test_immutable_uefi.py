import unittest
from immutable_uefi_evidence import verify, report, PHASES
from immutable_evidence import PHASE_MARKERS


class ImmutableUefiTests(unittest.TestCase):
    def test_requires_firmware_and_complete_boot_order(self):
        marker = "SUPRA_IMMUTABLE_UEFI_READY"
        ready = "SUPRA_TARGET_BOOT_READY"
        logs = {p: f"{marker}\r\n{PHASE_MARKERS[p]}\r\n{ready}\r\n" for p in PHASES}
        self.assertTrue(report(logs)["uefi_immutable_boot_verified"])
        self.assertFalse(report(logs)["automatic_rollback_verified"])
        for bad in (
            f"{PHASE_MARKERS['first']}\n{ready}\n",
            f"{PHASE_MARKERS['first']}\n{marker}\n{ready}\n",
            logs["first"] + "SUPRA_IMMUTABLE_ERROR\n",
            marker + "\n" + logs["first"],
        ):
            with self.subTest(log=bad), self.assertRaises(ValueError):
                verify("first", bad)
