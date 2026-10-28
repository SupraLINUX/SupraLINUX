#!/usr/bin/env python3
"""Freeze reviewed private runtime trees without following their symbolic links."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--plan', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = Path.cwd().resolve()
assert a.output.resolve().is_relative_to(root / '.work') and not a.output.exists()
plan = json.loads(a.plan.read_text())
a.output.mkdir()
copied, excluded = {}, []
for item in plan['inputs']:
    source = Path(item['source']).absolute()
    destination = Path(item['destination'])
    assert source.exists() and not source.is_symlink()
    assert not destination.is_absolute() and '..' not in destination.parts
    entries = sorted(source.rglob('*')) if source.is_dir() else [source]
    for entry in entries:
        rel = entry.relative_to(source) if source.is_dir() else Path()
        target = a.output / destination / rel
        if entry.is_symlink():
            resolved = entry.resolve()
            if not resolved.exists():
                assert item.get('exclude_broken_symlinks') is True
                excluded.append({'source': str(entry), 'target': str(entry.readlink()),
                                 'reason': 'Broken input link; no runtime bytes replaced'})
                continue
            assert resolved.is_relative_to(source), 'Input link escapes its reviewed tree'
            assert not target.exists() and not target.is_symlink()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(entry.readlink())
        elif entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif entry.is_file():
            assert not target.exists()
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry, target)
            digest = hashlib.file_digest(entry.open('rb'), 'sha256').hexdigest()
            assert hashlib.file_digest(target.open('rb'), 'sha256').hexdigest() == digest
            copied[str(target.relative_to(a.output))] = {'source': str(entry), 'sha256': digest,
                                                        'size': entry.stat().st_size}
        else:
            raise AssertionError('Unsupported input type: ' + str(entry))
for item in plan.get('diagnostic_symlinks', []):
    dest = a.output / item['destination']
    assert not dest.exists() and not dest.is_symlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(item['target'])
for link in a.output.rglob('*'):
    if link.is_symlink():
        assert link.resolve().exists() and link.resolve().is_relative_to(a.output.resolve())
review = {'schema': 1, 'state': 'PAYLOAD MATERIALIZATION PASS', 'regular_files': copied,
          'excluded_broken_symlinks': excluded, 'diagnostic_symlinks': plan.get('diagnostic_symlinks', []),
          'original_input_bytes_unchanged': True, 'host_packages_installed': False,
          'canonical_effect': 'none', 'package_attempt_consumed': False}
(a.output.parent / (a.output.name + '-materialization.json')).write_text(json.dumps(review, indent=2)+'\n')
print(json.dumps({'state': review['state'], 'files': len(copied), 'excluded_links': len(excluded)}))
