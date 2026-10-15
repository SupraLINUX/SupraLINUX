"""Transport one connector-selected original artifact; never print credentials or bodies."""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import time
import zipfile
from pathlib import Path


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository', required=True)
    p.add_argument('--metadata', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert a.repository == 'SupraLINUX/SupraLINUX'
    root = Path.cwd().resolve()
    assert any(a.output.resolve().is_relative_to(root/x) for x in ('.work', '.artifacts'))
    meta = json.loads(a.metadata.read_text())
    artifact_id = meta['id']
    assert type(artifact_id) is int and artifact_id > 0 and meta['expired'] is False
    expected = meta['digest'].removeprefix('sha256:')
    assert re.fullmatch('[0-9a-f]{64}', expected)
    assert not a.output.exists() and not a.output.is_symlink()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    receipt = a.output.with_suffix('.transport.json')
    assert not receipt.exists()
    attempts = []
    for number in range(1, 4):
        partial = a.output.with_suffix(f'.read{number}.partial')
        assert not partial.exists()
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with partial.open('xb') as f:
            try:
                r = subprocess.run(['gh', 'api', f'repos/{a.repository}/actions/artifacts/{artifact_id}/zip'],
                                   stdout=f, stderr=subprocess.PIPE, timeout=900)
                rc = r.returncode
            except subprocess.TimeoutExpired:
                rc = 124
        valid = rc == 0 and digest(partial) == expected and partial.stat().st_size == meta['size_in_bytes']
        if valid:
            with zipfile.ZipFile(partial) as z:
                valid = z.testzip() is None
        attempts.append({'read': number, 'started_at': started, 'exit_code': rc,
                         'bytes': partial.stat().st_size, 'sha256': digest(partial), 'valid': valid})
        if valid:
            partial.rename(a.output)
            break
        # Keep failed transport bytes private for diagnosis, without emitting them.
        if number < 3:
            time.sleep(5 * number)
    result = {'schema': 1, 'state': 'PASS' if a.output.is_file() else 'TRANSPORT FAIL',
              'repository': a.repository, 'artifact_id': artifact_id, 'expected_sha256': expected,
              'metadata_sha256': digest(a.metadata), 'attempts': attempts,
              'credential_or_response_output': False, 'host_network_modified': False,
              'package_attempt_consumed': False, 'operator_source_sha256': digest(Path(__file__))}
    receipt.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('state', 'artifact_id', 'expected_sha256')}))
    raise SystemExit(0 if result['state'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
