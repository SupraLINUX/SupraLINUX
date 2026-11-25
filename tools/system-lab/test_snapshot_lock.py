import unittest
from snapshot_lock import lock, validate_config

CFG = {"schema_version":1,"architecture":"x86_64","snapshot":"2026/11/24",
       "repositories":["core","extra"],"packages":["base"],
       "builder":"docker.io/library/archlinux@sha256:"+"a"*64}
HASHES = {"core":"b"*64,"extra":"c"*64}
ROW = "core|base|1-1|any|"+"d"*64+"|base-1-1-any.pkg.tar.zst|https://archive.archlinux.org/repos/2026/11/24/core/os/x86_64/base-1-1-any.pkg.tar.zst"

class SnapshotTests(unittest.TestCase):
    def test_lock(self):
        r=lock(CFG,[ROW],HASHES)
        self.assertEqual(r["packages"][0]["name"],"base")
        self.assertFalse(r["package_signatures_verified"])
        self.assertFalse(r["release_signed"])
    def test_rejects_rolling(self):
        with self.assertRaises(ValueError):
            lock(CFG,[ROW.replace("2026/11/24","last")],HASHES)
    def test_missing_duplicate_malformed(self):
        for rows in [[],[ROW,ROW],["bad"]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                lock(CFG,rows,HASHES)
    def test_builder_and_date(self):
        for updates in [{"builder":"archlinux:latest"},{"snapshot":"last"},{"snapshot":"2026/02/30"}]:
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                validate_config(dict(CFG,**updates))
    def test_database_hashes(self):
        with self.assertRaises(ValueError):
            lock(CFG,[ROW],{"core":"b"*64})

if __name__=="__main__":
    unittest.main()
