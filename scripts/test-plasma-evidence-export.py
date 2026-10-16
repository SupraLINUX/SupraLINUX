#!/usr/bin/env python3
"""Reject altered, unsealed or ordinary missing evidence during hidden-file recovery."""
import hashlib
import importlib.machinery
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE = importlib.machinery.SourceFileLoader('exporter', str(Path(__file__).with_name('plasma-evidence-export.py'))).load_module()


class ExportTests(unittest.TestCase):
    def fixture(self, directory, missing='build/.qt/generated.cmake', sealed=True):
        root = Path(directory)
        payload = root/'guest-files/workspace/evidence/authoritative-plasma-package'
        (payload/Path(missing).parent).mkdir(parents=True)
        data = b'original generated CMake input\n'
        (payload/missing).write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        result = {'files_sha256':{missing:digest}}
        result_bytes = json.dumps(result).encode()
        (payload/'result.json').write_bytes(result_bytes)
        seal = f'{digest}  ./{(payload/missing).relative_to(root)}\n' if sealed else ''
        (root/'evidence-sha256.txt').write_text(seal)
        archive_path = root/'actions.zip'
        with zipfile.ZipFile(archive_path,'w') as archive:
            archive.writestr('result.json', result_bytes)
        return root, payload, result, archive_path

    def test_recovers_original_hidden_bytes_only_with_sealed_host(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _, result, path = self.fixture(temp)
            with zipfile.ZipFile(path) as archive:
                with self.assertRaises(AssertionError):
                    MODULE.verify_export(archive,result)
                recovered = MODULE.verify_export(archive,result,root)
            self.assertEqual(recovered, {'build/.qt/generated.cmake':b'original generated CMake input\n'})

    def test_rejects_nonhidden_omission_and_unsealed_payload(self):
        for missing,sealed in [('build/generated.cmake',True),('build/.qt/generated.cmake',False)]:
            with self.subTest(missing=missing,sealed=sealed), tempfile.TemporaryDirectory() as temp:
                root, _, result, path = self.fixture(temp,missing,sealed)
                with zipfile.ZipFile(path) as archive, self.assertRaises(AssertionError):
                    MODULE.verify_export(archive,result,root)

    def test_rejects_modified_guest_bytes_or_result(self):
        for changed in ['build/.qt/generated.cmake','result.json']:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temp:
                root, payload, result, path = self.fixture(temp)
                (payload/changed).write_bytes(b'changed')
                with zipfile.ZipFile(path) as archive, self.assertRaises(AssertionError):
                    MODULE.verify_export(archive,result,root)

    def test_rejects_altered_present_file_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _, result, path = self.fixture(temp)
            with zipfile.ZipFile(path,'a') as archive:
                archive.writestr('build/.qt/generated.cmake',b'changed')
            with zipfile.ZipFile(path) as archive, self.assertRaises(AssertionError):
                MODULE.verify_export(archive,result,root)
            result['files_sha256'] = {'../.secret':hashlib.sha256(b'x').hexdigest()}
            with zipfile.ZipFile(path) as archive, self.assertRaises(AssertionError):
                MODULE.verify_export(archive,result,root)


if __name__ == '__main__':
    unittest.main()
