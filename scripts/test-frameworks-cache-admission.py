#!/usr/bin/env python3
"""Regression: stale or modified cache content must never feed a package build."""
import importlib.machinery
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cache = importlib.machinery.SourceFileLoader("cache", str(ROOT / "scripts/admit-frameworks-cache.py")).load_module()
access = importlib.machinery.SourceFileLoader("access", str(ROOT / "scripts/check-qemu-image-access.py")).load_module()


class ImageAccess(unittest.TestCase):
    def test_named_user_acl_is_masked(self):
        acl = {("user", ""): "rwx", ("group", ""): "r-x", ("other", ""): "---",
               ("mask", ""): "r--", ("user", "64055"): "r-x"}
        self.assertNotIn("x", access.permissions(acl, 1000, 1000, 64055, {991}))
        acl[("mask", "")] = "r-x"
        self.assertIn("x", access.permissions(acl, 1000, 1000, 64055, {991}))

    def test_owner_permissions_take_precedence(self):
        acl = {("user", ""): "---", ("group", ""): "r-x", ("other", ""): "rwx"}
        self.assertNotIn("r", access.permissions(acl, 1000, 1000, 1000, {1000}))

    def test_group_union_is_masked_without_other_fallback(self):
        acl = {("user", ""): "rwx", ("group", ""): "---", ("other", ""): "rwx",
               ("group", "991"): "r-x", ("mask", ""): "r--"}
        self.assertNotIn("x", access.permissions(acl, 1000, 1000, 64055, {991}))


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

    def admit(self, plan=None, revalidated=()):
        return cache.admit(self.root, self.record, self.dag, self.plan if plan is None else plan, revalidated)

    def repair(self, source_package='kf6-extra-cmake-modules'):
        source = self.root/'repair'
        (source/'DEBIAN').mkdir(parents=True)
        version = '6.30.0-0supralinux4'
        (source/'DEBIAN/control').write_text(
            f'Package: extra-cmake-modules\nSource: {source_package}\nVersion: {version}\nArchitecture: all\n'
            'Maintainer: Test <test@example.invalid>\nDescription: Revalidated cache input fixture\n')
        deb = self.root/'repaired.deb'
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(source), str(deb)], check=True, stdout=subprocess.DEVNULL)
        reference = {'path': 'verified-repair.json', 'sha256': '0'*64}
        self.dag['nodes']['extra-cmake-modules'].update(package_version=version, revalidation=reference)
        predecessor = self.record['frameworks_predecessors']['extra-cmake-modules']
        predecessor['version'] = version
        predecessor['binaries'][0]['sha256'] = cache.digest(deb)
        return {'node': 'extra-cmake-modules', 'path': str(deb), 'version': version,
                'source_package': 'kf6-extra-cmake-modules', 'revalidation': reference,
                'artifact_sha256': '1'*64, **predecessor['binaries'][0]}

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

    def test_repair_selected_without_modifying_historical_pool(self):
        original_digest = cache.digest(self.deb)
        item = self.repair()
        self.assertEqual([selected['path'] for selected in self.admit(revalidated=[item])], [item['path']])
        self.assertEqual(cache.digest(self.deb), original_digest)

    def test_superseded_version_rejected_after_repair(self):
        original = copy.deepcopy(self.record)
        item = self.repair()
        self.record = original
        with self.assertRaises(AssertionError):
            self.admit(revalidated=[item])

    def test_repaired_binary_tampering_rejected(self):
        item = self.repair()
        path = Path(item['path'])
        path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaisesRegex(AssertionError, 'Corrupt revalidated'):
            self.admit(revalidated=[item])

    def test_repaired_source_identity_rejected(self):
        item = self.repair(source_package='different-source')
        with self.assertRaisesRegex(AssertionError, 'source mismatch'):
            self.admit(revalidated=[item])

    def test_support_selected_without_replacing_historical_pool(self):
        original = cache.digest(self.deb)
        item = self.repair()
        item['retained_support'] = item.pop('revalidation')
        node = self.dag['nodes']['extra-cmake-modules']
        node['retained_support'] = node.pop('revalidation')
        selected = self.admit(revalidated=[item])
        self.assertEqual(selected[0]['retained_support'], item['retained_support'])
        self.assertEqual(cache.digest(self.deb), original)

    def test_unreviewed_support_proof_rejected(self):
        item = self.repair()
        item['retained_support'] = item.pop('revalidation')
        node = self.dag['nodes']['extra-cmake-modules']
        node['retained_support'] = node.pop('revalidation')
        item['retained_support'] = {'path': 'different-proof.json', 'sha256': '2'*64}
        with self.assertRaises(AssertionError):
            self.admit(revalidated=[item])


if __name__ == "__main__":
    unittest.main()
