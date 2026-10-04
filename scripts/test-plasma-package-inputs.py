#!/usr/bin/env python3
"""Regression checks for source admission and substantive theme validation."""
import copy
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
prepare = importlib.machinery.SourceFileLoader("prepare", str(ROOT / "scripts/prepare-plasma-package.py")).load_module()
resources = importlib.machinery.SourceFileLoader("resources", str(ROOT / "packages/plasma/breeze-grub/debian/tests/theme-resources")).load_module()


class InputAdmission(unittest.TestCase):
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

    def test_upgrade_setup_keeps_candidate_after_os_release(self):
        script = (ROOT / "scripts/run-authoritative-plasma-package.sh").read_text()
        setup = re.search(r'^(SETUP=".*?\n)\s*set \+e', script, flags=re.M | re.S).group(1)
        candidate = json.loads((ROOT / "manifests/kde-plasma-package-build.json").read_text())["nodes"]["breeze-grub"]["version"]
        env = {**os.environ, "PACKAGE_VERSION": candidate, "VERSION": candidate,
               "BASELINE_PACKAGE": "grub-theme-breeze"}
        output = subprocess.check_output(["bash", "-c", ". /etc/os-release\n" + setup +
                                          "printf '%s' \"$SETUP\""], text=True, env=env)
        comparison = next(line for line in output.splitlines() if line.startswith("dpkg --compare-versions"))
        self.assertEqual(shlex.split(comparison)[2], candidate)

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
