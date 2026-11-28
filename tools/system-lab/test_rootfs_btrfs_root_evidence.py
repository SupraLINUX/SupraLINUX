import unittest

from rootfs_btrfs_root_evidence import report


class BtrfsRootEvidenceTests(unittest.TestCase):
    def test_two_distinct_ordered_markers(self):
        result = report("SUPRA_BTRFS_ROOT_PREPARED\r\nSUPRA_TARGET_BOOT_READY\r\n",
                        "SUPRA_BTRFS_ROOT_READY\nSUPRA_TARGET_BOOT_READY\n")
        self.assertTrue(result["btrfs_root_boot_verified"])
        self.assertFalse(result["single_disk_uefi_verified"])

    def test_missing_or_reordered_markers(self):
        good = "SUPRA_BTRFS_ROOT_PREPARED\nSUPRA_TARGET_BOOT_READY\n"
        for boot in ("SUPRA_TARGET_BOOT_READY\n",
                     "SUPRA_TARGET_BOOT_READY\nSUPRA_BTRFS_ROOT_READY\n",
                     "SUPRA_BTRFS_ROOT_READY\nSUPRA_BTRFS_ROOT_READY\nSUPRA_TARGET_BOOT_READY\n"):
            with self.subTest(boot=boot), self.assertRaises(ValueError):
                report(good, boot)
