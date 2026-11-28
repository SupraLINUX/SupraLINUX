import copy
import unittest
from layer_plan import plan_delta


class LayerPlanTests(unittest.TestCase):
    def setUp(self):
        self.base = {"packages": [{"name": "glibc", "version": "1-1"}]}
        self.fixture = {"base_lock_sha256": "a" * 64, "snapshot": "2026/11/24",
                        "package": {"name": "tree", "version": "2-1", "arch": "x86_64",
                                    "filename": "tree.pkg.tar.zst", "sha256": "b" * 64},
                        "depends": ["glibc"], "compressed_bytes": 10, "installed_bytes": 20}
        self.fields = {"NAME": ["tree"], "VERSION": ["2-1"], "ARCH": ["x86_64"],
                       "FILENAME": ["tree.pkg.tar.zst"], "SHA256SUM": ["b" * 64],
                       "DEPENDS": ["glibc"], "CSIZE": ["10"], "ISIZE": ["20"]}

    def test_additive_only(self):
        original = copy.deepcopy(self.base)
        plan = plan_delta(self.base, self.fixture, self.fields)
        self.assertEqual(plan["expected_inventory"], {"glibc": "1-1", "tree": "2-1"})
        self.assertEqual(self.base, original)
        self.assertFalse(plan["transaction_verified"])
        self.assertFalse(plan["layer_signature_verified"])

    def test_reject_metadata_drift(self):
        for key, value in (("DEPENDS", ["glibc", "extra"]), ("CONFLICTS", ["glibc"]),
                           ("REPLACES", ["glibc"]), ("SHA256SUM", ["c" * 64]),
                           ("ISIZE", ["21"])):
            with self.subTest(key=key):
                fields = dict(self.fields, **{key: value})
                with self.assertRaises(ValueError):
                    plan_delta(self.base, self.fixture, fields)

    def test_missing_dependency_or_already_installed(self):
        for packages in ([], self.base["packages"] + [{"name": "tree", "version": "2-1"}]):
            with self.assertRaises(ValueError):
                plan_delta({"packages": packages}, self.fixture, self.fields)
