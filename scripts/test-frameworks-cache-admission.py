#!/usr/bin/env python3
"""Regression: stale or modified cache content must never feed a package build."""
import importlib.machinery
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cache = importlib.machinery.SourceFileLoader("cache", str(ROOT / "scripts/admit-frameworks-cache.py")).load_module()


class CacheAdmission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pool = self.root / "repo/pool"
        self.pool.mkdir(parents=True)
        source = self.root / "fixture"
        (source / "DEBIAN").mkdir(parents=True)
        (source / "DEBIAN/control").write_text(
            "Package: extra-cmake-modules\nSource: kf6-extra-cmake-modules\nVersion: 6.30.0-0supralinux3\n"
            "Architecture: all\nMaintainer: Test <test@example.invalid>\nDescription: Cache admission fixture\n")
        self.deb = self.pool / "ecm.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(source), str(self.deb)],
                       check=True, stdout=subprocess.DEVNULL)
        binary = {"package": "extra-cmake-modules", "architecture": "all", "sha256": cache.digest(self.deb)}
        predecessor = {"version": "6.30.0-0supralinux3", "source_package": "kf6-extra-cmake-modules", "binaries": [binary]}
        self.record = {"frameworks_predecessors": {"extra-cmake-modules": predecessor}}
        self.dag = {"nodes": {"extra-cmake-modules": {"state": "PASS", "package_version": predecessor["version"],
                                                   "source_package": predecessor["source_package"]}}}
        (self.root / "artifact-plan.json").write_text('{"fixture":true}\n')
        self.plan = (self.root / "artifact-plan.json").read_bytes()
        (self.root / "package-pool.json").write_text(json.dumps({"package_count": 1, "packages": [
            {"file": "ecm.deb", "version": predecessor["version"], "size": self.deb.stat().st_size, **binary}]}))
        (self.root / "repo/Packages").write_text("fixture index")
        text = "cache_only=yes\nframework_packages_preinstalled_in_sbuild_rootfs=no\n"
        for path, key in [("artifact-plan.json", "artifact_plan_sha256"), ("package-pool.json", "package_pool_sha256"),
                          ("repo/Packages", "packages_index_sha256")]:
            text += f"{key}={cache.digest(self.root / path)}\n"
        (self.root / "checkpoint-manifest.txt").write_text(text)

    def admit(self, plan=None):
        return cache.admit(self.root, self.record, self.dag, self.plan if plan is None else plan)

    def test_exact_input_admitted(self):
        self.assertEqual([item["path"] for item in self.admit()], [str(self.deb)])

    def test_binary_tampering_rejected(self):
        self.deb.write_bytes(self.deb.read_bytes() + b"changed")
        with self.assertRaisesRegex(AssertionError, "Corrupt cache binary"):
            self.admit()

    def test_stale_plan_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Stale Frameworks"):
            self.admit(b"different current selection")

    def test_apt_index_tampering_rejected(self):
        (self.root / "repo/Packages").write_text("different index")
        with self.assertRaisesRegex(AssertionError, "Corrupt cache metadata"):
            self.admit()

    def test_unreviewed_binary_digest_rejected(self):
        self.record["frameworks_predecessors"]["extra-cmake-modules"]["binaries"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(AssertionError, "reviewed contract"):
            self.admit()

    def test_nonpass_predecessor_rejected(self):
        self.dag["nodes"]["extra-cmake-modules"]["state"] = "FAIL"
        with self.assertRaises(AssertionError):
            self.admit()


if __name__ == "__main__":
    unittest.main()
