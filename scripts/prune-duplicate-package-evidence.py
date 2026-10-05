#!/usr/bin/env python3
"""Drop only byte-identical testbed copies of retained canonical package files."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def prune(evidence):
    canonical = {p.name:p for p in (evidence/'packages').iterdir() if p.is_file() and p.suffix in {'.deb','.ddeb'}}
    assert canonical and all(not p.is_symlink() for p in canonical.values())
    checksums = {name:digest(path) for name,path in canonical.items()}
    by_digest = {checksums[name]:path for name,path in sorted(canonical.items())}
    removed = [];distinct = []
    for path in sorted((evidence/'autopkgtest').rglob('*')):
        if path.suffix not in {'.deb','.ddeb'} or not path.is_file():continue
        assert not path.is_symlink() and path.resolve().is_relative_to((evidence/'autopkgtest').resolve())
        actual = digest(path)
        counterpart = by_digest.get(actual)
        if counterpart is None and path.name not in canonical:continue
        entry = {'path':str(path.relative_to(evidence)), 'canonical_path':str((counterpart or canonical[path.name]).relative_to(evidence)),
                 'sha256':actual, 'size':path.stat().st_size}
        if counterpart is None:
            distinct.append(entry)
            continue
        removed.append(entry)
        path.unlink()
    return {'state':'PASS','kind':'byte-identical-package-evidence-deduplication', 'canonical_payloads_unchanged':True,
            'removed_copies':removed,'retained_distinct_payloads':distinct,'bytes_saved':sum(item['size'] for item in removed)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path)
    args = parser.parse_args()
    result = prune(args.evidence)
    (args.evidence/'package-copy-deduplication.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f"Package evidence deduplication: PASS; removed={len(result['removed_copies'])}; bytes saved={result['bytes_saved']}")


if __name__ == '__main__':main()
