import pathlib
import subprocess
import tempfile
import unittest

HELPER = pathlib.Path(__file__).with_name("snapshot_download.sh").resolve()


class SnapshotDownloadTest(unittest.TestCase):
    def run_case(self, codes):
        with tempfile.TemporaryDirectory() as tmp:
            script = r'''
set -euo pipefail
source "$1"
cd "$2"
printf 'original' > result
printf '%s\n' "$3" > codes
curl() {
    printf '%s\n' "$*" >> calls
    local index code output=''
    index=$(wc -l < calls)
    code=$(sed -n "${index}p" codes)
    while (( $# )); do
        if [[ $1 == --output ]]; then output=$2; shift; fi
        shift
    done
    printf 'partial-%s' "$index" > "$output"
    printf '%s' "${code#*:}"
    return "${code%%:*}"
}
sleep() { :; }
if download https://archive.archlinux.org/example result; then
    echo 0 > rc
else
    echo "$?" > rc
fi
'''
            subprocess.run(
                ["bash", "-c", script, "_", str(HELPER), tmp, "\n".join(codes)],
                check=True,
            )
            root = pathlib.Path(tmp)
            self.assertEqual(list(root.glob("result.part.*")), [])
            calls = (root / "calls").read_text().splitlines()
            for call in calls:
                self.assertIn("--proto =https --proto-redir =https", call)
                self.assertIn("--fail", call)
                self.assertNotIn("--retry", call)
            return int((root / "rc").read_text()), (root / "result").read_text(), calls

    def test_http2_reset_switches_to_http1_and_discards_partial(self):
        rc, body, calls = self.run_case(["92:200", "28:000", "0:200"])
        self.assertEqual((rc, body, len(calls)), (0, "partial-3", 3))
        self.assertNotIn("--http1.1", calls[0])
        self.assertTrue(all("--http1.1" in call for call in calls[1:]))

    def test_retry_budget(self):
        rc, body, calls = self.run_case(["92:200", "92:200", "92:200"])
        self.assertEqual((rc, body, len(calls)), (92, "original", 3))

    def test_permanent_http_and_tls_errors_do_not_retry(self):
        for code in ("22:404", "60:000", "23:200"):
            with self.subTest(code=code):
                rc, body, calls = self.run_case([code])
                self.assertEqual((rc, body, len(calls)), (int(code.split(":")[0]), "original", 1))

    def test_transient_http(self):
        rc, body, calls = self.run_case(["22:503", "0:200"])
        self.assertEqual((rc, body, len(calls)), (0, "partial-2", 2))
