#!/usr/bin/env python3
"""Reject native fixture admissions with changed inputs, coverage or cleanup evidence."""
import copy
import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare', ROOT / 'scripts/prepare-plasma-package.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
records = json.loads((ROOT / 'manifests/kde-plasma-package-build.json').read_text())['nodes']
checked = 0
for record in records.values():
    if 'native_fixture_review' not in record:
        continue
    prepare.check_native_fixture_review(record)
    original_path = ROOT / record['native_fixture_review']['path']
    original_proof = json.loads(original_path.read_text())
    for mutation in ['source', 'candidate-certification', 'coverage', 'helper', 'cleanup', 'unbound-evidence']:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / original_path.parent.relative_to(ROOT)
            shutil.copytree(original_path.parent, directory)
            proof = copy.deepcopy(original_proof)
            if mutation == 'source':
                proof['upstream_sha256'] = '0' * 64
            elif mutation == 'candidate-certification':
                proof['candidate_certification'] = True
            elif mutation == 'unbound-evidence':
                del proof['files_sha256'][proof['native_stdout']]
            else:
                name = proof[{'coverage': 'native_result', 'helper': 'helper_calls', 'cleanup': 'direct_cleanup'}[mutation]]
                file = directory / name
                payload = json.loads(file.read_text())
                if mutation == 'coverage':
                    next(iter(payload['controls'].values()))['skipped'] = 1
                elif mutation == 'helper':
                    payload[0]['exit_code'] = 1
                else:
                    payload['direct_uuid_absent'] = False
                file.write_text(json.dumps(payload) + '\n')
                proof['files_sha256'][name] = hashlib.sha256(file.read_bytes()).hexdigest()
            file = directory / original_path.name
            file.write_text(json.dumps(proof) + '\n')
            mutated = copy.deepcopy(record)
            mutated['native_fixture_review']['sha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
            try:
                prepare.check_native_fixture_review(mutated, root)
            except AssertionError:
                checked += 1
            else:
                raise AssertionError('Accepted invalid native fixture: ' + mutation)
assert checked > 0, 'No current native fixture review exercised'
print('Native fixture source, scope, coverage, helper, cleanup and evidence rejection checks PASS', checked)
