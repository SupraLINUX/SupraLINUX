import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).with_name("layer_digest.sh").resolve()


class DigestTests(unittest.TestCase):
    def digest(self, root):
        return subprocess.check_output(["bash", "-c", 'source "$1"; layer_digest "$2"', "_", str(HELPER), str(root)], text=True)

    def test_content_mode_links_and_xattrs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a"
            a.write_bytes(b"original")
            os.link(a, root / "b")
            a.chmod(0o644)
            baseline = self.digest(root)
            self.assertEqual(baseline, self.digest(root))
            a.chmod(0o600)
            self.assertNotEqual(baseline, self.digest(root))
            a.chmod(0o644)
            self.assertEqual(baseline, self.digest(root))
            os.setxattr(a, "user.supra", b"metadata")
            self.assertNotEqual(baseline, self.digest(root))
            os.removexattr(a, "user.supra")
            self.assertEqual(baseline, self.digest(root))
            a.write_bytes(b"modified")
            self.assertNotEqual(baseline, self.digest(root))
