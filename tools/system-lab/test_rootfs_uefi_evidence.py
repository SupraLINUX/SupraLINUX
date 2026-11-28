import unittest
from rootfs_uefi_evidence import report


class UefiTests(unittest.TestCase):
    def test_firmware_and_target_markers(self):
        result = report("SUPRA_UEFI_BOOT_READY\r\nSUPRA_TARGET_BOOT_READY\r\n")
        self.assertTrue(result["uefi_boot_verified"])
        self.assertFalse(result["secure_boot_verified"])

    def test_incomplete_evidence(self):
        for log in ("SUPRA_TARGET_BOOT_READY", "SUPRA_UEFI_BOOT_READY",
                    "SUPRA_TARGET_BOOT_READY\nSUPRA_UEFI_BOOT_READY",
                    "SUPRA_UEFI_BOOT_READY\nSUPRA_UEFI_BOOT_READY\nSUPRA_TARGET_BOOT_READY"):
            with self.subTest(log=log), self.assertRaises(ValueError):
                report(log)
