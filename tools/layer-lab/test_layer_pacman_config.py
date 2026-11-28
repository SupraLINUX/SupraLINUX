import pathlib
import subprocess
import tempfile
import unittest

HELPER = pathlib.Path(__file__).with_name("layer_pacman_config.sh")


class LayerPacmanConfigTests(unittest.TestCase):
    def test_absolute_target_hook_directory_and_required_signatures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "target"
            root.mkdir()
            config = pathlib.Path(tmp) / "pacman.conf"
            subprocess.run(
                ["bash", "-ec", 'source "$1"; write_layer_pacman_config "$2" "$3"',
                 "bash", str(HELPER), str(root), str(config)], check=True)
            self.assertEqual(config.read_text().splitlines(), [
                "[options]", "Architecture = x86_64", "SigLevel = Required",
                "LocalFileSigLevel = Required",
                f"HookDir = {root}/etc/pacman.d/hooks",
            ])
            self.assertTrue((root / "etc/pacman.d/hooks").is_dir())
            self.assertFalse((root / "etc/pacman.d/hooks/zz-supra-interrupt.hook").exists())

    def test_reject_non_target_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = pathlib.Path(tmp) / "pacman.conf"
            for root in ("/", "relative"):
                result = subprocess.run(
                    ["bash", "-ec", 'source "$1"; write_layer_pacman_config "$2" "$3"',
                     "bash", str(HELPER), root, str(config)])
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(config.exists())
