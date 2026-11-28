import unittest
from bootcount_evidence import verify, CANDIDATES, POINT


class BootCountTests(unittest.TestCase):
    def test_exact_counter_and_actual_kill_required(self):
        listing = "::/loader/entries/supra-immutable-staged.conf\n::/loader/entries/" + CANDIDATES["trial1"] + "\n"
        console = "SUPRA_BOOTCOUNT_PATH=/loader/entries/" + CANDIDATES["trial1"] + "\r\nSUPRA_IMMUTABLE_UEFI_READY\r\n" + POINT + "\r\n"
        injection = {"marker": POINT, "returncode": -9, "signal": "SIGKILL"}
        verify("trial1", listing, console, injection)
        for bad in (listing.replace("+1-1", "+2"), listing + "extra.conf\n"):
            with self.assertRaises(ValueError):
                verify("trial1", bad, console, injection)
        with self.assertRaises(ValueError):
            verify("trial1", listing, console, None)
        with self.assertRaises(ValueError):
            verify("trial1", listing, console + "SUPRA_TARGET_BOOT_READY\n", injection)

    def test_fallback_requires_exhausted_candidate(self):
        listing = "supra-immutable-staged.conf\nsupra-immutable-layer+0-2.conf\n"
        log = "SUPRA_IMMUTABLE_UEFI_READY\nSUPRA_BOOTCOUNT_FALLBACK_READY\nSUPRA_TARGET_BOOT_READY\n"
        verify("fallback", listing, log)
        with self.assertRaises(ValueError):
            verify("fallback", listing.replace("+0-2", "+1-1"), log)
