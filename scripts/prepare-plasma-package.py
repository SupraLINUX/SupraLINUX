#!/usr/bin/env python3
"""Materialize an explicitly reviewed packaging overlay on verified KDE sources."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_campaign():
    relative = Path(os.environ.get('SUPRALINUX_PACKAGE_CAMPAIGN', 'manifests/kde-plasma-package-build.json'))
    assert not relative.is_absolute() and '..' not in relative.parts
    assert relative in {Path('manifests/kde-plasma-package-build.json'), Path('manifests/package-revalidation.json')}
    return json.loads((ROOT / relative).read_text())


def packaging_hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def supplementary_contract(node, record, root=ROOT, packaging=None):
    """Bind a supplementary overlay to the independently reviewed source authority."""
    assert record['source_scope'] == 'plasma-supplementary-provider'
    providers = json.loads((root/'manifests/kde-plasma-supplementary-providers.json').read_text())
    provider = providers['nodes'][node]
    candidate = provider['candidate_provider']
    assert candidate['signature_verification'] == 'PASS'
    assert provider['qt_provider_effect'] == 'none'
    assert record['source_package'] == node
    for field, source in [('upstream_version', 'upstream_version'), ('upstream_url', 'upstream_url'),
                          ('upstream_sha256', 'upstream_sha256'), ('signature_sha256', 'signature_sha256'),
                          ('signing_fingerprint', 'signing_primary_fingerprint')]:
        assert record[field] == candidate[source], f'Supplementary source changed: {field}'
    retained = providers['source_review_retention']
    payload = (root/retained['path']).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == retained['sha256']
    references = [item for item in json.loads(payload)['ubuntu_sources'] if item['source_package'] == node]
    assert len(references) == 1
    reference = references[0]
    assert record['packaging_reference_version'] == reference['version']
    archive = next(item for item in reference['archives'] if item['name'].endswith('.debian.tar.xz'))
    assert record['packaging_reference_sha256'] == archive['sha256']
    assert record['packaging_reference_kind'] == 'authenticated-ubuntu-debian-archive'
    subprocess.run(['dpkg', '--compare-versions', record['version'], 'gt', reference['version']], check=True)
    assert record['version'].split('-')[0] == record['upstream_version'], 'Unexpected provider epoch/version'
    assert record['packaging_path'] == f'packages/plasma/{node}/debian'
    relative = Path(record['signing_key_path']).relative_to(record['packaging_path'])
    assert '..' not in relative.parts and not relative.is_absolute()
    packaging = packaging if packaging is not None else root/record['packaging_path']
    key = packaging/relative
    assert key.resolve().is_relative_to(packaging.resolve()) and not key.is_symlink()
    assert hashlib.sha256(key.read_bytes()).hexdigest() == record['packaging_sha256'][str(relative)]


def contract(node):
    campaign = load_campaign()
    record = campaign["nodes"][node]
    assert record["packaging_review"] == "PASS", "Packaging requires individual review"
    if campaign['role'] == 'reviewed-plasma-package-build':
        if record.get('source_scope', 'plasma-level0') == 'plasma-supplementary-provider':
            supplementary_contract(node, record)
        else:
            assert record.get('source_scope', 'plasma-level0') == 'plasma-level0'
            level = json.loads((ROOT / "manifests/kde-plasma-level0.json").read_text())["nodes"][node]
            assert record["version"] == level["candidate_package_version"], "Candidate version mismatch"
            assert record["upstream_sha256"] == level["upstream_source_sha256"], "Source mismatch"
    else:
        assert campaign['role'] == 'reviewed-package-revalidation'
        original = json.loads((ROOT / 'manifests/kde-dag.json').read_text())['nodes'][node]
        assert record['upstream_sha256'] == original['source_sha256']
        assert record['source_package'] == original['source_package']
        subprocess.run(['dpkg', '--compare-versions', record['version'], 'gt', record['supersedes']['version']], check=True)
    assert packaging_hashes(ROOT / record["packaging_path"]) == record["packaging_sha256"], "Packaging inputs changed"
    return campaign, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("node")
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    _, record = contract(args.node)
    assert hashlib.sha256(args.upstream.read_bytes()).hexdigest() == record["upstream_sha256"], "Upstream tarball digest"
    assert not args.output.exists(), "Refusing to overwrite prepared sources"
    args.output.mkdir(parents=True)
    source_name = record["source_package"]
    upstream_version = record["upstream_version"]
    orig = args.output / f"{source_name}_{upstream_version}.orig.tar.xz"
    shutil.copyfile(args.upstream, orig)
    with tarfile.open(orig) as archive:
        prefix = f"{args.node}-{upstream_version}"
        assert all(m.name == prefix or m.name.startswith(prefix + "/") for m in archive), "Unexpected source root"
        archive.extractall(args.output, filter="data")
    source = args.output / prefix
    shutil.copytree(ROOT / record["packaging_path"], source / "debian",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name, reference in record.get('symbols_baselines', {}).items():
        assert Path(name).name == name and name.endswith('.symbols')
        path = ROOT / reference['path']
        assert path.resolve().is_relative_to(ROOT) and not path.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == reference['sha256']
        assert not (source / 'debian' / name).exists()
        shutil.copyfile(path, source / 'debian' / name)
    actual = subprocess.check_output(["dpkg-parsechangelog", "-l", str(source / "debian/changelog"), "-S", "Version"], text=True).strip()
    assert actual == record["version"], "Changelog version mismatch"
    subprocess.run(["dpkg-source", "-b", str(source)], cwd=args.output, check=True)
    print(args.output / f"{source_name}_{record['version'].split(':')[-1]}.dsc")


if __name__ == "__main__":
    main()
