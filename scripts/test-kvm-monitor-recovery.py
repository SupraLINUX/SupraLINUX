#!/usr/bin/env python3
"""Exercise the actual active-job monitor through an unavailable control plane."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
core=(ROOT/'scripts/run-kvm-jit-gate-core.sh').read_text()
loop=core.split("printf 'Bound gate to workflow run ID",1)[1]
loop=loop[loop.index('DEADLINE='):loop.index("printf 'Waiting for bound workflow run")]


class MonitorTests(unittest.TestCase):
    def run_monitor(self,exited=False,timeout=60):
        with tempfile.TemporaryDirectory() as temp:
            env={**os.environ,'EVIDENCE_DIR':temp,'JOB_TIMEOUT_SECONDS':str(timeout),'SUPRALINUX_MONITOR_READ_FAULTS':'1'}
            functions='''set -Eeuo pipefail
date() { if [[ "$1" == +%s ]]; then printf '100\\n'; else printf 'fixture-time\\n'; fi; }
sleep() { :; }
runner_snapshot() { printf ''; }
guest_runner_status() { printf '%s' '''+"'"+json.dumps({'return':{'exited':exited}})+"'"+'''; }
'''
            result=subprocess.run(['bash','-c',functions+loop],env=env,capture_output=True,text=True)
            files={p.name:p.read_text() for p in Path(temp).iterdir()}
            return result,files

    def test_read_outage_keeps_running_guest_until_api_recovers(self):
        result,files=self.run_monitor()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(files['monitor-guest-process.json'])['exited'],False)
        self.assertIn('checking guest process without stopping VM',files['monitor-read-outages.txt'])

    def test_guest_exit_can_finish_monitor_without_api(self):
        result,files=self.run_monitor(exited=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(files['monitor-guest-process.json'])['exited'])

    def test_unavailable_control_plane_does_not_remove_deadline(self):
        result,files=self.run_monitor(timeout=0)
        self.assertEqual(result.returncode,1)
        self.assertIn('Timed out waiting for the JIT runner job to finish',result.stderr)
        self.assertFalse(json.loads(files['monitor-guest-process.json'])['exited'])


if __name__ == '__main__':unittest.main()
