#!/usr/bin/env python3
"""Verify old package identities for an upgrade test, never as build inputs."""
import argparse
import hashlib
import importlib.machinery
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
prepare = importlib.machinery.SourceFileLoader('prepare', str(ROOT/'scripts/prepare-plasma-package.py')).load_module()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node')
    parser.add_argument('--payload', type=Path, default=Path('/var/lib/supralinux/milestones/frameworks-6.30'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    _, record = prepare.contract(args.node)
    original = record['retained_upgrade']
    assert not args.output.exists(), 'Refusing to replace retained upgrade inputs'
    args.output.mkdir(parents=True)
    pool = json.loads((args.payload/'package-pool.json').read_text())
    selected = []
    for binary in original['binaries']:
        matches = [item for item in pool['packages'] if item['package'] == binary['package']
                   and item['version'] == original['version'] and item['architecture'] == binary['architecture']]
        assert len(matches) == 1
        item = matches[0]
        assert Path(item['file']).name == item['file']
        path = args.payload/'repo/pool'/item['file']
        assert not path.is_symlink()
        digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        assert digest == binary['sha256'] == item['sha256']
        fields = [subprocess.check_output(['dpkg-deb','-f',str(path),field],text=True).strip()
                  for field in ['Package','Source','Version','Architecture']]
        assert fields == [binary['package'], original['source_package'], original['version'], binary['architecture']]
        shutil.copyfile(path, args.output/path.name)
        selected.append({'path':str(path), 'package':fields[0], 'version':fields[2], 'architecture':fields[3], 'sha256':digest})
    args.evidence.write_text(json.dumps({'state':'PASS', 'scope':'historical-upgrade-baseline-inputs',
                                       'eligible_as_build_predecessors':False, 'selected':selected},indent=2)+'\n')
    print(f'Historical upgrade test inputs verified: {len(selected)} binaries; no package Attempt')


if __name__ == '__main__':
    main()
