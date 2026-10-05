#!/usr/bin/env python3
"""Exercise recovery, permanent failure, bounded retries and clean response output."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReadRetry(unittest.TestCase):
    def run_transport(self, replies):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base/'replies.json').write_text(json.dumps(replies))
            curl = base/'curl'
            curl.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
root=Path(os.environ['FIXTURE_ROOT']);counter=root/'count'
n=int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(n+1));r=json.loads((root/'replies.json').read_text())[n]
args=sys.argv[1:];Path(args[args.index('--output')+1]).write_text(r['body'])
print(r['status'],end='');sys.exit(r['rc'])
''')
            curl.chmod(0o755)
            env = {**os.environ, 'PATH':str(base)+os.pathsep+os.environ['PATH'],
                   'FIXTURE_ROOT':str(base), 'SUPRALINUX_API_RETRY_DELAY_SECONDS':'0'}
            result = subprocess.run([str(ROOT/'scripts/github-read-with-retry.sh'), 'https://api.github.com/example'],
                                    env=env, capture_output=True, text=True)
            return result, int((base/'count').read_text())

    def test_dns_and_http_unavailability_recover_without_partial_response(self):
        result, count = self.run_transport([
            {'rc':6,'status':'000','body':'partial'},
            {'rc':22,'status':'503','body':'unavailable'},
            {'rc':0,'status':'200','body':'{"state":"ok"}'}])
        self.assertEqual(result.returncode,0)
        self.assertEqual(count,3)
        self.assertEqual(json.loads(result.stdout),{'state':'ok'})

    def test_authorization_failure_is_not_retried(self):
        result, count = self.run_transport([{'rc':22,'status':'403','body':'forbidden'}])
        self.assertEqual((result.returncode,count),(22,1))
        self.assertEqual(result.stdout,'')

    def test_network_outage_has_finite_budget(self):
        result, count = self.run_transport([{'rc':6,'status':'000','body':''}]*8)
        self.assertEqual((result.returncode,count),(6,8))


if __name__ == '__main__':
    unittest.main()
