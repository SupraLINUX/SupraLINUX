import unittest
from prepare_rootfs import validate_installed


class RootfsTests(unittest.TestCase):
    def test_exact_closure(self):
        packages = [{"name": "base", "version": "1:2-3"}, {"name": "linux", "version": "4-1"}]
        self.assertEqual(validate_installed(packages, ["linux 4-1", "base 1:2-3"]), 2)
        for rows in (["base 1:2-3"], ["linux 4-2", "base 1:2-3"],
                     ["linux 4-1", "base 1:2-3", "extra 1"],
                     ["linux 4-1", "base 1:2-3", "base 1:2-3"]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate_installed(packages, rows)
