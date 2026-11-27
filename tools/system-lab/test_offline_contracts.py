import pathlib
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


class ResolverPolicyTests(unittest.TestCase):
    def test_timeout_and_transport_only(self):
        cases = [(124, 240, "", True), (137, 250, "", True),
                 (137, 10, "", False), (1, 10, "connection reset", True),
                 (1, 10, "metadata mismatch", False)]
        with tempfile.TemporaryDirectory() as tmp:
            log = pathlib.Path(tmp) / "log"
            for status, elapsed, content, expected in cases:
                with self.subTest(status=status, elapsed=elapsed, content=content):
                    log.write_text(content)
                    run = subprocess.run(
                        ["bash", "-c", 'source "$1"; resolver_retryable "$2" "$3" "$4"',
                         "test", str(HERE / "snapshot_retry_policy.sh"), str(status),
                         str(elapsed), str(log)], check=False)
                    self.assertEqual(run.returncode == 0, expected)


class InitramfsConfigTests(unittest.TestCase):
    def test_removes_only_autodetect_and_adds_modules(self):
        command = '''
set -eu
MODULES=(existing)
HOOKS=(base systemd autodetect microcode modconf block filesystems fsck)
source "$1"
printf '%s\\n' "${MODULES[*]}" "${HOOKS[*]}"
'''
        result = subprocess.run(["bash", "-c", command, "test",
                                 str(HERE / "rootfs_btrfs_mkinitcpio.conf")],
                                check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.splitlines(),
                         ["existing btrfs virtio_pci virtio_blk",
                          "base systemd microcode modconf block filesystems fsck"])
