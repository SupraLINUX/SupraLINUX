#!/usr/bin/env python3
"""Check canonical payload scoping and source closure in mixed CI artifacts."""
import hashlib
import importlib.machinery
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
retention = importlib.machinery.SourceFileLoader("retention", str(ROOT / "scripts/retain-package-artifacts.py")).load_module()


class PayloadScope(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "deb/DEBIAN").mkdir(parents=True)
        (self.root / "deb/DEBIAN/control").write_text(
            "Package: fixture\nSource: fixture\nVersion: 1.0\nArchitecture: all\n"
            "Maintainer: Test <test@example.invalid>\nDescription: Artifact scope fixture\n")
        deb = self.root / "fixture_1.0_all.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(self.root / "deb"), str(deb)],
                       check=True, stdout=subprocess.DEVNULL)
        payload = {"fixture_1.0.orig.tar.xz": b"fixture source bytes", "fixture_1.0_all.deb": deb.read_bytes()}
        def checksums(names):
            return "\n".join(f" {hashlib.sha256(payload[n]).hexdigest()} {len(payload[n])} {n}" for n in names)
        payload["fixture_1.0.dsc"] = ("Source: fixture\nVersion: 1.0\nChecksums-Sha256:\n" +
                                       checksums(["fixture_1.0.orig.tar.xz"]) + "\n").encode()
        payload["fixture_1.0_all.buildinfo"] = b"Source: fixture\nVersion: 1.0\nArchitecture: all\n"
        payload["fixture_1.0_all.changes"] = ("Source: fixture\nVersion: 1.0\nChecksums-Sha256:\n" +
                                               checksums(list(payload)) + "\n").encode()
        self.payload = {"packages/" + name: data for name, data in payload.items()}
        # Infrastructure probes retain their own metadata and duplicate log/result basenames.
        self.payload.update({"result.json": b"root", "cache-probe/result.json": b"probe",
                             "cache-probe/probe_1.0.dsc": b"Source: probe\nVersion: 1.0\n",
                             "cache-probe/probe_1.0_all.changes": b"Source: probe\nVersion: 1.0\n",
                             "cache-probe/probe_1.0_all.deb": b"unrelated probe bytes"})

    def inspect(self, prefix="packages/"):
        archive = self.root / "artifact.zip"
        with zipfile.ZipFile(archive, "w") as handle:
            for name, payload in self.payload.items():
                handle.writestr(name, payload)
        item = {"node": "fixture", "package_version": "1.0", "artifact_sha256": retention.sha256(archive),
                "payload_prefix": prefix}
        return retention.inspect(archive, item, "fixture")

    def test_mixed_artifact_admits_only_candidate(self):
        result = self.inspect()
        self.assertTrue(result["source_payload_verified"])
        self.assertEqual([item["package"] for item in result["binaries"]], ["fixture"])

    def test_unscoped_ambiguous_artifact_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate artifact basenames"):
            self.inspect("")

    def test_wrong_source_scope_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not identify"):
            self.inspect("cache-probe/")

    def test_source_checksum_tampering_rejected(self):
        self.payload["packages/fixture_1.0.orig.tar.xz"] = b"different source bytes"
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.inspect()

    def test_unsafe_scope_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsafe canonical"):
            self.inspect("../packages/")


if __name__ == "__main__":
    unittest.main()
