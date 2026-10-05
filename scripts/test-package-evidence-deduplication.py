#!/usr/bin/env python3
"""Prove evidence compaction never removes canonical or distinct payloads."""
import importlib.machinery
import tempfile
import unittest
from pathlib import Path

MODULE = importlib.machinery.SourceFileLoader('compact',str(Path(__file__).with_name('prune-duplicate-package-evidence.py'))).load_module()


class DedupTests(unittest.TestCase):
    def test_removes_only_identical_copies_and_preserves_sources_clients_and_distinct_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);(root/'packages').mkdir();(root/'autopkgtest/binaries').mkdir(parents=True)
            for name,data in [('candidate.deb',b'canonical'),('candidate.ddeb',b'debug'),('source.tar.xz',b'source')]:
                (root/'packages'/name).write_bytes(data)
            (root/'autopkgtest/binaries/candidate.deb').write_bytes(b'canonical')
            (root/'autopkgtest/binaries/candidate.ddeb').write_bytes(b'distinct debug')
            (root/'autopkgtest/binaries/dependency.deb').write_bytes(b'dependency')
            (root/'autopkgtest/client').write_bytes(b'Ubuntu compiled client')
            result = MODULE.prune(root)
            self.assertEqual(result['bytes_saved'],9)
            self.assertEqual(len(result['removed_copies']),1)
            self.assertEqual(len(result['retained_distinct_payloads']),1)
            self.assertFalse((root/'autopkgtest/binaries/candidate.deb').exists())
            self.assertEqual((root/'packages/candidate.deb').read_bytes(),b'canonical')
            for path in ['packages/source.tar.xz','autopkgtest/client','autopkgtest/binaries/candidate.ddeb','autopkgtest/binaries/dependency.deb']:
                self.assertTrue((root/path).is_file())

    def test_rejects_symlink_copies_without_deleting_them(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'packages').mkdir();(root/'autopkgtest').mkdir()
            (root/'packages/candidate.deb').write_bytes(b'canonical')
            path=root/'autopkgtest/candidate.deb';path.symlink_to('../packages/candidate.deb')
            with self.assertRaises(AssertionError):MODULE.prune(root)
            self.assertTrue(path.is_symlink())
            self.assertEqual((root/'packages/candidate.deb').read_bytes(),b'canonical')


if __name__ == '__main__':unittest.main()
