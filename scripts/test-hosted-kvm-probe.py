#!/usr/bin/env python3
"""Reject false positives from the isolated hosted QEMU/KVM probe."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hosted_kvm", ROOT / "scripts/probe-hosted-kvm.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class HostedKVMProbeTests(unittest.TestCase):
    def test_boot_sector_signature_and_debug_exit(self):
        sector = probe.boot_sector()
        self.assertEqual(len(sector), 512)
        self.assertEqual(sector[-2:], b"\\x55\\xaa")
        self.assertIn(bytes((0xBA, 0xF4, 0, 0xB0, probe.EXIT_VALUE, 0xEE)), sector)
        self.assertEqual(probe.EXPECTED_QEMU_EXIT, 85)

    def test_acceleration_cannot_fall_back_to_tcg(self):
        cmd = probe.kvm_command(Path("/tmp/example.img"))
        self.assertEqual(cmd[cmd.index("-machine") + 1], "pc,accel=kvm")
        self.assertEqual(cmd[cmd.index("-cpu") + 1], "host")
        self.assertNotIn("tcg", " ".join(cmd))
        self.assertIn("isa-debug-exit,iobase=0xf4,iosize=0x04", cmd)

    def test_correct_exit_and_guest_marker_both_required(self):
        with tempfile.TemporaryDirectory():
            with mock.patch.object(probe, "check_environment", return_value={"PRETTY_NAME": "Ubuntu 26.04"}):
                for code, msg, passed in [
                    (85, probe.MARKER + "\\n", True),
                    (85, "SeaBIOS loaded only", False),
                    (0, probe.MARKER + "\\n", False),
                    (1, probe.MARKER + "\\n", False),
                ]:
                    sample = mock.Mock(returncode=code, stdout=msg)
                    with mock.patch.object(probe.subprocess, "run", return_value=sample):
                        with self.subTest(code=code, msg=msg):
                            if passed:
                                self.assertEqual(probe.run_probe()["qemu_exit_code"], 85)
                            else:
                                with self.assertRaisesRegex(RuntimeError, "KVM guest proof failed"):
                                    probe.run_probe()


if __name__ == "__main__":
    unittest.main()
