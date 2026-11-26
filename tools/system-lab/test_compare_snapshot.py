import copy
import unittest

from compare_snapshot import compare


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.digest = "a" * 64
        self.lock = {"builder": "pinned", "snapshot": "2026/11/24",
                     "packages": [{"name": "base", "sha256": "b" * 64}]}
        self.verification = {"schema_version": 1, "kind": "snapshot-signature-evidence",
                             "candidate_lock_sha256": self.digest, "builder": "pinned",
                             "package_signatures_verified": True, "release_signed": False,
                             "packages": [{"name": "base", "sha256": "b" * 64,
                                           "signer": "C" * 40}]}

    def test_agreement_is_not_rootfs_reproducibility(self):
        result = compare(self.lock, copy.deepcopy(self.lock), self.verification, self.digest)
        self.assertTrue(result["independent_resolution_equal"])
        self.assertFalse(result["rootfs_reproducible"])

    def test_mismatch(self):
        changed = copy.deepcopy(self.lock)
        changed["packages"][0]["sha256"] = "d" * 64
        with self.assertRaises(ValueError):
            compare(self.lock, changed, self.verification, self.digest)

    def test_evidence_mismatch_or_incomplete(self):
        for patch in ({"candidate_lock_sha256": "e" * 64},
                      {"package_signatures_verified": False}, {"packages": []},
                      {"release_signed": True}, {"builder": "other"}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                compare(self.lock, self.lock, {**self.verification, **patch}, self.digest)
