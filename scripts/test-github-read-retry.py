#!/usr/bin/env python3
"""Exercise recovery, permanent failure, bounded retries and clean response output."""
import json
import hashlib
import importlib.util
import os
import subprocess
import tempfile
import traceback
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class ReadRetry(unittest.TestCase):
    def run_transport(self, replies, url='https://api.github.com/example'):
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
(root/'args.json').write_text(json.dumps(args))
print(r['status'],end='');sys.exit(r['rc'])
''')
            curl.chmod(0o755)
            env = {**os.environ, 'PATH':str(base)+os.pathsep+os.environ['PATH'],
                   'FIXTURE_ROOT':str(base), 'SUPRALINUX_API_RETRY_DELAY_SECONDS':'0'}
            result = subprocess.run([str(ROOT/'scripts/github-read-with-retry.sh'), url],
                                    env=env, capture_output=True, text=True)
            self.transport_args = json.loads((base/'args.json').read_text())
            return result, int((base/'count').read_text())

    def test_dns_and_http_unavailability_recover_without_partial_response(self):
        result, count = self.run_transport([
            {'rc':6,'status':'000','body':'partial'},
            {'rc':22,'status':'503','body':'unavailable'},
            {'rc':0,'status':'200','body':'{"state":"ok"}'}])
        self.assertEqual(result.returncode,0)
        self.assertEqual(count,3)
        self.assertEqual(json.loads(result.stdout),{'state':'ok'})
        self.assertEqual(self.transport_args[self.transport_args.index('--max-time')+1], '30')

    def test_authorization_failure_is_not_retried(self):
        result, count = self.run_transport([{'rc':22,'status':'403','body':'forbidden'}])
        self.assertEqual((result.returncode,count),(22,1))
        self.assertEqual(result.stdout,'')

    def test_network_outage_has_finite_budget(self):
        result, count = self.run_transport([{'rc':6,'status':'000','body':''}]*8)
        self.assertEqual((result.returncode,count),(6,8))

    def test_artifact_read_has_longer_finite_budget_without_partial_output(self):
        result, count = self.run_transport([{'rc':28,'status':'200','body':'partial-binary-secret'}]*3,
            'https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/123/zip')
        self.assertEqual((result.returncode,count),(28,3))
        self.assertEqual(result.stdout,'')
        self.assertNotIn('partial-binary-secret',result.stderr)
        for option,value in [('--max-time','900'),('--speed-limit','1024'),('--speed-time','60')]:
            self.assertEqual(self.transport_args[self.transport_args.index(option)+1],value)

    def test_only_exact_artifact_endpoint_gets_longer_budget(self):
        for url in ['https://api.github.com/repos/a/b/actions/artifacts',
                    'https://api.github.com/repos/a/b/actions/artifacts/123/zip/unrelated',
                    'https://example.invalid/repos/a/b/actions/artifacts/123/zip']:
            with self.subTest(url=url):
                result, count = self.run_transport([{'rc':0,'status':'200','body':'ok'}],url)
                self.assertEqual((result.returncode,count),(0,1))
                self.assertEqual(self.transport_args[self.transport_args.index('--max-time')+1],'30')


class ArtifactFailureDiagnostics(unittest.TestCase):
    def test_frameworks_and_supplementary_failures_do_not_print_authentication(self):
        for filename in ['prepare-frameworks-revalidation-inputs.py','supplementary-package-inputs.py']:
            with self.subTest(module=filename), tempfile.TemporaryDirectory() as directory:
                spec = importlib.util.spec_from_file_location('transport_fixture',ROOT/'scripts'/filename)
                module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                base=Path(directory);token='FAKE_SENSITIVE_TOKEN'
                metadata={'archive_download_url':'https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/1/zip'}
                failed=subprocess.CompletedProcess(['transport','Authorization: Bearer '+token],28)
                if filename.startswith('prepare-frameworks'):
                    (base/'manifests').mkdir();(base/'manifests/kde-dag.json').write_text('{}')
                    proof={'archive_path':'.artifacts/missing.zip','artifact_sha256':'0'*64,'artifact_id':1}
                    (base/'proof.json').write_text(json.dumps(proof));(base/'artifact-meta.json').write_text(json.dumps(metadata))
                    nodes={'fixture':{'revalidation':{'path':'proof.json','sha256':hashlib.sha256((base/'proof.json').read_bytes()).hexdigest()}}}
                    record={'frameworks_predecessors':{'fixture':{}}}
                    patches=[mock.patch.object(module,'ROOT',base),
                             mock.patch.object(module.effective,'effective_nodes',return_value=nodes),
                             mock.patch.object(module.effective,'check_requested')]
                else:
                    record={'supplementary_predecessors':{'fixture':{'evidence':{
                        'archive_root':'.artifacts/missing','artifact_sha256':'0'*64,'artifact_id':1}}}}
                    patches=[mock.patch.object(module,'checked_contract',return_value=({},metadata))]
                from contextlib import ExitStack
                with ExitStack() as stack:
                    for patch in patches:stack.enter_context(patch)
                    stack.enter_context(mock.patch.object(module.subprocess,'run',return_value=failed))
                    try:
                        module.materialize(record,base/'output',archive_root=base,token=token)
                    except RuntimeError as error:
                        diagnostic=''.join(traceback.format_exception(error))
                        self.assertIn('transport failed (exit=28)',diagnostic)
                        self.assertNotIn(token,diagnostic)
                        self.assertNotIn('CalledProcessError',diagnostic)
                    else:self.fail('Failed artifact transport was accepted')


if __name__ == '__main__':
    unittest.main()
