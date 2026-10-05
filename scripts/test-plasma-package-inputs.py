#!/usr/bin/env python3
"""Regression checks for source admission and substantive theme validation."""
import copy
import hashlib
import importlib.machinery
import json
import os
import re
import shlex
import subprocess
import struct
import zlib
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
testing = importlib.machinery.SourceFileLoader("testing", str(ROOT / "scripts/plasma-package-testing.py")).load_module()
prepare = importlib.machinery.SourceFileLoader("prepare", str(ROOT / "scripts/prepare-plasma-package.py")).load_module()
resources = importlib.machinery.SourceFileLoader("resources", str(ROOT / "packages/plasma/breeze-grub/debian/tests/theme-resources")).load_module()
sounds = importlib.machinery.SourceFileLoader("sounds", str(ROOT / "packages/plasma/ocean-sound-theme/debian/tests/sound-resources")).load_module()


class InputAdmission(unittest.TestCase):
    def test_sound_alias_target_change_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "alias.oga").symlink_to("outside.oga")
            with self.assertRaisesRegex(AssertionError, "alias target changed"):
                sounds.verify(root, {"alias.oga": {"symlink": "original.oga"}})

    def test_broken_sound_alias_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "alias.oga").symlink_to("missing.oga")
            with self.assertRaisesRegex(AssertionError, "broken or escapes"):
                sounds.verify(root, {"alias.oga": {"symlink": "missing.oga"}})

    def test_png_timestamp_change_only_is_allowed(self):
        def chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
        def png(year, pixel):
            return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) +
                    chunk(b"tIME", struct.pack(">H5B", year, 1, 1, 0, 0, 0)) +
                    chunk(b"IDAT", zlib.compress(b"\0" + pixel)) + chunk(b"IEND", b""))
        original = resources.resource_hash(png(2016, b"\0\0\0\xff"), "test.png")
        self.assertEqual(original, resources.resource_hash(png(2026, b"\0\0\0\xff"), "test.png"))
        self.assertNotEqual(original, resources.resource_hash(png(2026, b"\xff\0\0\xff"), "test.png"))
        damaged = bytearray(png(2026, b"\0\0\0\xff")); damaged[-1] ^= 1
        with self.assertRaisesRegex(AssertionError, "Invalid PNG CRC"):
            resources.resource_hash(bytes(damaged), "test.png")

    def test_upgrade_setup_keeps_reviewed_candidate(self):
        record = json.loads((ROOT / "manifests/kde-plasma-package-build.json").read_text())["nodes"]["breeze-grub"]
        output = testing.setup_commands(ROOT, record)
        comparison = next(line for line in output.splitlines() if line.startswith("dpkg --compare-versions"))
        self.assertEqual(shlex.split(comparison)[2], record["version"])
        self.assertIn('plasma-package-testing.py" setup "${NODE}',
                      (ROOT / "scripts/run-authoritative-plasma-package.sh").read_text())

    def test_upstream_suite_cannot_pass_with_missing_or_failed_tests(self):
        record = {"upstream_tests": ["first", "second"]}
        log = "1/2 Test #1: first ..... Passed 0.01 sec\n2/2 Test #2: second ..... Passed 0.02 sec\n100% tests passed, 0 tests failed out of 2"
        self.assertEqual(testing.upstream_test_result(record, log)["state"], "PASS")
        for broken in [log.replace("Passed", "Failed", 1), log.replace("second", "wrong"),
                       log.replace("out of 2", "out of 1")]:
            with self.subTest(broken=broken), self.assertRaises(AssertionError):
                testing.upstream_test_result(record, broken)

    def test_additional_ecm_tests_are_accounted_for(self):
        record = {"upstream_tests": ["decoration"]}
        log = "1/2 Test #1: appstreamtest ..... Passed 0.01 sec\n2/2 Test #2: decoration ..... Passed 0.01 sec\n100% tests passed, 0 tests failed out of 2"
        result = testing.upstream_test_result(record, log)
        self.assertEqual(result["executed_tests"], ["appstreamtest", "decoration"])
        with self.assertRaises(AssertionError):
            testing.upstream_test_result(record, log.replace("appstreamtest ..... Passed", "appstreamtest ..... Failed"))
        with self.assertRaises(AssertionError):
            testing.upstream_test_result(record, log.replace("out of 2", "out of 1"))

    def test_baseline_setup_rejects_changed_or_unreviewed_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package/tests").mkdir(parents=True)
            setup = root / "package/tests/setup"
            setup.write_text("#!/bin/sh\nprintf 'fixture\\n'\n")
            record = {"ubuntu_baseline_package": "baseline-fixture", "version": "4:6.7.5-0supralinux1",
                      "packaging_path": "package", "baseline_setup_script": "tests/setup",
                      "packaging_sha256": {"tests/setup": hashlib.sha256(setup.read_bytes()).hexdigest()}}
            commands = testing.setup_commands(root, record)
            subprocess.run(["bash", "-n"], input=commands, text=True, check=True)
            self.assertIn("base64 --decode", commands)
            for path in ["../outside", "/absolute", "control"]:
                bad = copy.deepcopy(record); bad["baseline_setup_script"] = path
                with self.subTest(path=path), self.assertRaises(AssertionError):
                    testing.setup_commands(root, bad)
            setup.write_text("changed")
            with self.assertRaisesRegex(AssertionError, "Setup inputs changed"):
                testing.setup_commands(root, record)

    def test_changed_packaging_rejected(self):
        original = prepare.packaging_hashes
        try:
            prepare.packaging_hashes = lambda path: {"changed": "bad"}
            with self.assertRaisesRegex(AssertionError, "Packaging inputs changed"):
                prepare.contract("breeze-grub")
        finally:
            prepare.packaging_hashes = original

    def test_unreviewed_source_rejected(self):
        original = prepare.json.loads
        def changed(payload):
            result = original(payload)
            if result.get("role") == "reviewed-plasma-package-build":
                result = copy.deepcopy(result)
                result["nodes"]["breeze-grub"]["packaging_review"] = "REVIEW_REQUIRED"
            return result
        try:
            prepare.json.loads = changed
            with self.assertRaisesRegex(AssertionError, "individual review"):
                prepare.contract("breeze-grub")
        finally:
            prepare.json.loads = original

    def test_corrupt_installed_resource_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            theme = Path(directory)
            (theme / "theme.txt").write_text("corrupt")
            with self.assertRaisesRegex(AssertionError, "differs from signed upstream"):
                resources.verify(theme, {"theme.txt": "0" * 64})

    def test_extra_installed_resource_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            theme = Path(directory)
            (theme / "unexpected.png").write_bytes(b"unexpected")
            with self.assertRaisesRegex(AssertionError, "resource set changed"):
                resources.verify(theme, {})


if __name__ == "__main__":
    unittest.main()
