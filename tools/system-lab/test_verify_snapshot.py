import unittest
from verify_snapshot import reconcile

HASH = "a" * 64
FPR = "B" * 40
PACKAGES = [{"name": "base", "sha256": HASH}]
ROW = f"base\t{HASH}\t{FPR}"


class VerificationTests(unittest.TestCase):
    def test_complete(self):
        self.assertEqual(reconcile(PACKAGES, [ROW])[0]["signer"], FPR)

    def test_rejects_incomplete_or_duplicate(self):
        for rows in ([], [ROW, ROW], [ROW.replace("base", "other")]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                reconcile(PACKAGES, rows)

    def test_rejects_bad_digest_or_signer(self):
        for row in (ROW.replace(HASH, "c" * 64), ROW.replace(FPR, "bad"), "bad"):
            with self.subTest(row=row), self.assertRaises(ValueError):
                reconcile(PACKAGES, [row])
