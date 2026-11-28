import subprocess
import unittest
from pathlib import Path
from immutable_evidence import report


class ImmutableTests(unittest.TestCase):
    def test_layout_excludes_shared_var_and_pacman_database(self):
        helper = Path(__file__).with_name("immutable_layout.sh")
        for role in ("staged", "layer"):
            output = subprocess.check_output(
                ["bash", "-ec", 'source "$1"; immutable_fstab "$2"', "bash", str(helper), role],
                text=True)
            lines = [line.split() for line in output.splitlines()]
            self.assertEqual(lines[0][:4], ["LABEL=SUPRA_BTRFS_ROOT", "/", "btrfs",
                                            f"ro,subvol=immutable/{role}"])
            self.assertEqual({row[1] for row in lines[1:]},
                             {"/home", "/var/log", "/var/cache", "/var/lib/systemd", "/var/tmp", "/tmp"})

    def test_missing_or_failed_boot_rejected(self):
        logs = {p: f"SUPRA_IMMUTABLE_{m}\nSUPRA_TARGET_BOOT_READY\n"
                for p, m in (("prepare", "PREPARED"), ("first", "FIRST_READY"),
                             ("next", "NEXT_READY"), ("return", "RETURN_READY"))}
        self.assertTrue(report(logs)["readonly_deployment_boot_verified"])
        self.assertFalse(report(logs)["atomic_activation_verified"])
        with self.assertRaises(ValueError):
            report(dict(logs, next="SUPRA_TARGET_BOOT_READY\n"))
