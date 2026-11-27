import pathlib
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


class InitramfsDriverTests(unittest.TestCase):
    def check(self, builtin, archive, ok):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [pathlib.Path(tmp) / n for n in ("builtin", "archive")]
            for path, content in zip(paths, (builtin, archive)):
                path.write_text(content)
            result = subprocess.run(["bash", str(HERE / "rootfs_initramfs_drivers.sh"),
                                     "6.18.65-1-lts", *map(str, paths)],
                                    text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode == 0, ok, result.stderr)
            return result

    def test_builtin_and_modules(self):
        result = self.check("kernel/fs/btrfs/btrfs.ko\n",
                            "usr/lib/modules/6.18.65-1-lts/kernel/virtio-pci.ko.zst\n"
                            "usr/lib/modules/6.18.65-1-lts/kernel/virtio_blk.ko\n", True)
        self.assertEqual(result.stdout.splitlines(),
                         ["btrfs\tbuiltin", "virtio_pci\tinitramfs", "virtio_blk\tinitramfs"])

    def test_all_builtin(self):
        self.check("kernel/btrfs.ko\nkernel/virtio_pci.ko\nkernel/virtio-blk.ko\n",
                   "init\n", True)

    def test_wrong_kernel_or_name_rejected(self):
        self.check("kernel/not_btrfs.ko\nkernel/virtio_pci.ko\nkernel/virtio_blk.ko\n",
                   "usr/lib/modules/other/kernel/btrfs.ko\n", False)

    def test_missing_virtio_rejected(self):
        self.check("kernel/btrfs.ko\nkernel/virtio_pci.ko\n", "init\n", False)
