import unittest
from rootfs_btrfs_evidence import report


class BtrfsEvidenceTests(unittest.TestCase):
    def test_complete(self):
        result = report("SUPRA_BTRFS_LAB_READY\r\nSUPRA_TARGET_BOOT_READY\r\n")
        self.assertTrue(result["staging_isolated"])
        self.assertFalse(result["actual_package_layer_verified"])
        self.assertFalse(result["atomic_boot_switch_verified"])

    def test_reject_partial(self):
        for log in ("SUPRA_TARGET_BOOT_READY", "SUPRA_BTRFS_LAB_READY",
                    "SUPRA_TARGET_BOOT_READY\nSUPRA_BTRFS_LAB_READY"):
            with self.subTest(log=log), self.assertRaises(ValueError):
                report(log)
