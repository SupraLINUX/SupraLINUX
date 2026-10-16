#!/usr/bin/env python3
"""Verify an export and recover only omitted hidden files from its sealed guest."""
import hashlib
from pathlib import Path, PurePosixPath


def verify_export(archive, result, host_dir=None):
    names = archive.namelist()
    assert len(names) == len(set(names)), 'Duplicate exported paths'
    recovered = {}
    for name, digest in result['files_sha256'].items():
        parts = PurePosixPath(name).parts
        assert parts and not name.startswith('/') and all(p not in {'.', '..'} for p in parts), 'Unsafe evidence path'
        if name in names:
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
            continue
        assert host_dir is not None and any(p.startswith('.') for p in parts), f'Missing exported evidence: {name}'
        payload_dir = host_dir/'guest-files/workspace/evidence/authoritative-plasma-package'
        path = payload_dir/name
        assert path.resolve().is_relative_to(payload_dir.resolve()) and path.is_file(), name
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, f'Sealed guest payload changed: {name}'
        seal_entries = {}
        for line in (host_dir/'evidence-sha256.txt').read_text().splitlines():
            checksum, seal_path = line.split('  ', 1)
            seal_entries[seal_path.removeprefix('./')] = checksum
        relative = str(path.relative_to(host_dir))
        assert seal_entries.get(relative) == digest, f'Payload not covered by host seal: {name}'
        assert (payload_dir/'result.json').read_bytes() == archive.read('result.json'), 'Guest result differs from Actions'
        recovered[name] = data
    return recovered
