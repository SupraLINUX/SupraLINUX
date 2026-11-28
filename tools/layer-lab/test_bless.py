import unittest
from bless_evidence import verify


class BlessTests(unittest.TestCase):
    def test_health_before_bless_and_persistent_entry(self):
        listing = "supra-immutable-staged.conf\nsupra-immutable-layer.conf\n"
        log = ("SUPRA_BLESS_COUNTED\r\nSUPRA_IMMUTABLE_UEFI_READY\r\n"
               "SUPRA_BLESS_HEALTH_READY\r\nSUPRA_BLESS_MARKED_GOOD\r\n"
               "SUPRA_BLESS_READY\r\nSUPRA_TARGET_BOOT_READY\r\n")
        verify("bless", listing, log)
        for bad in (log.replace("SUPRA_BLESS_HEALTH_READY\r\n", ""),
                    log.replace("SUPRA_BLESS_HEALTH_READY", "SUPRA_BLESS_MARKED_GOOD"),
                    log + "SUPRA_BLESS_CLEAN_BOOT\n"):
            with self.assertRaises(ValueError):
                verify("bless", listing, bad)
        with self.assertRaises(ValueError):
            verify("bless", listing.replace("layer.conf", "layer+1-1.conf"), log)
        verify("persist", listing, log.replace("SUPRA_BLESS_COUNTED", "SUPRA_BLESS_ALREADY_GOOD").replace("SUPRA_BLESS_MARKED_GOOD", "SUPRA_BLESS_CLEAN_BOOT"))
