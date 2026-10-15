#!/usr/bin/env python3
"""Cheap rejection tests for snapshot integrity and opt-in hosted guest lane."""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "guest_snapshot", ROOT / "scripts/hosted-ubuntu-guest-snapshot.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class GuestSnapshotTests(unittest.TestCase):
    def test_summary_requires_exact_pass_without_skip_or_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "summary"
            for lines, valid in [
                ("guest-smoke PASS\n", True),
                ("guest-smoke FAIL\n", False),
                ("guest-smoke SKIP\n", False),
                ("another-test PASS\n", False),
                ("guest-smoke PASS\nguest-smoke PASS\n", False),
                ("guest-smoke PASS\nother FAIL\n", False),
            ]:
                p.write_text(lines)
                with self.subTest(lines=lines):
                    if valid:
                        self.assertEqual(len(m.smoke(p)), 64)
                    else:
                        with self.assertRaises(AssertionError):
                            m.smoke(p)

    def test_no_backing_chain_is_admitted(self):
        with mock.patch.object(m.subprocess, "check_output", return_value=json.dumps({
            "format": "qcow2", "virtual-size": 8 * 1024 ** 3, "backing-filename": "/unsafe"
        })):
            with self.assertRaisesRegex(AssertionError, "independent"):
                m.image_info(Path("/not-needed.img"))

    def test_clean_sbuild_mechanism_scope_in_existing_hosted_vm(self):
        root = ROOT / "tests/fixtures/hosted-ubuntu-guest/debian/tests"
        control = (root / "control").read_text()
        script = root / "clean-sbuild-smoke"
        self.assertEqual(control.count("Tests: guest-smoke"), 1)
        self.assertEqual(control.count("Tests: clean-sbuild-smoke"), 1)
        self.assertIn("Depends: sbuild, mmdebstrap, dpkg-dev", control)
        self.assertTrue(script.is_file() and os.access(script, os.X_OK))
        content = script.read_text()
        self.assertIn('sbuild --chroot-mode=unshare --chroot="$WORK/resolute-amd64.tar"', content)
        self.assertIn("mmdebstrap --mode=root --variant=buildd", content)
        self.assertIn("env -u TMPDIR mmdebstrap", content)
        self.assertIn("SUPRALINUX_HOSTED_SBUILD_UNSHARE_SMOKE_PASS", content)
        self.assertIn("dpkg-deb -f", content)
        self.assertNotIn("sudo sbuild", content)
        subprocess.run(["bash", "-n", str(script)], check=True)

    def test_real_debian_source_fixture_is_complete(self):
        root = ROOT / "tests/fixtures/hosted-ubuntu-guest"
        changelog = root / "debian/changelog"
        control = (root / "debian/control").read_text()
        dep8 = (root / "debian/tests/control").read_text()
        smoke = root / "debian/tests/guest-smoke"
        self.assertTrue(changelog.is_file())
        self.assertTrue(smoke.is_file() and os.access(smoke, os.X_OK))
        self.assertIn("Package: supralinux-guest-probe", control)
        self.assertIn("Tests: guest-smoke", dep8)
        self.assertIn("Restrictions: isolation-machine", dep8)
        self.assertIn("test \"$VERSION_ID\" = 26.04", smoke.read_text())
        self.assertEqual(subprocess.check_output([
            "dpkg-parsechangelog", "-l", str(changelog), "-S", "Source"],
            text=True).strip(), "supralinux-guest-probe")
        self.assertEqual(subprocess.check_output([
            "dpkg-parsechangelog", "-l", str(changelog), "-S", "Version"],
            text=True).strip(), "1.0-1")
        lane = (ROOT / "scripts/hosted-ubuntu-guest-lane.sh").read_text()
        self.assertNotIn("cat > \"$FIXTURE/debian/control\"", lane)
        self.assertIn('FIXTURE="$ROOT/tests/fixtures/hosted-ubuntu-guest"', lane)

    def test_github_only_and_snapshot_after_smoke(self):
        wf = (ROOT / ".github/workflows/hosted-ubuntu-guest-probe.yml").read_text()
        sh = (ROOT / "scripts/hosted-ubuntu-guest-lane.sh").read_text()
        self.assertIn("types: [labeled]", wf)
        self.assertIn("ci:hosted-ubuntu-guest", wf)
        self.assertIn("runs-on: ubuntu-26.04", wf)
        self.assertIn("actions/cache/restore@0057852bfaa89a56745cba8c7296529d2fc39830", wf)
        self.assertIn("actions/cache/save@0057852bfaa89a56745cba8c7296529d2fc39830", wf)
        self.assertLess(wf.index("Run genuine QEMU-KVM DEP-8 guest test"),
                        wf.index("Seal new milestone snapshot after guest PASS"))
        self.assertLess(wf.index("Seal new milestone snapshot after guest PASS"),
                        wf.index("Cache only new sealed PASS milestone"))
        self.assertIn("test \"$RUNNER_ENVIRONMENT\" = github-hosted", sh)
        self.assertIn("--overlay-dir=", sh)
        self.assertIn("ubuntu-archive-keyring.gpg", sh)
        self.assertIn("timeout -k", sh)
        self.assertIn("sudo env -u TMPDIR autopkgtest-build-qemu", sh)
        self.assertNotIn('sudo env TMPDIR="$WORK/tmp" autopkgtest-build-qemu', sh)
        self.assertNotIn('"$EVID/base-build.log"', sh)
        self.assertIn("base-build-failure.txt", sh)


if __name__ == "__main__":
    unittest.main()
