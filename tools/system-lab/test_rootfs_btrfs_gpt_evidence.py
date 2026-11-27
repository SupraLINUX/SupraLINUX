import unittest
from rootfs_btrfs_gpt_evidence import MARKERS, report


class GptBootEvidenceTests(unittest.TestCase):
    def test_ordered_unique_markers(self):
        result = report("\r\n".join(MARKERS))
        self.assertTrue(result["single_disk_uefi_verified"])
        self.assertFalse(result["atomic_boot_switch_verified"])

    def test_missing_duplicate_reordered_and_failure_reject(self):
        for markers in (MARKERS[1:], MARKERS + MARKERS[:1],
                        MARKERS[::-1], MARKERS + ("SUPRA_BOOT_PROBE_FAILED result=exit-code",)):
            with self.subTest(markers=markers), self.assertRaises(ValueError):
                report("\n".join(markers))
