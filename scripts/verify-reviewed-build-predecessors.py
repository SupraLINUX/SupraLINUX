#!/usr/bin/env python3
"""Verify used predecessor versions without requiring unused available packages."""
import argparse
import hashlib
import importlib.machinery
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
prepare = importlib.machinery.SourceFileLoader('build_input_prepare', str(ROOT/'scripts/prepare-plasma-package.py')).load_module()
retention = importlib.machinery.SourceFileLoader('build_input_fields', str(ROOT/'scripts/retain-package-artifacts.py')).load_module()
RELATION = re.compile(r'([a-z0-9][a-z0-9+.-]*)(?::([a-z0-9-]+))?\s*\(=\s*([^\s)]+)\)')
NAME = re.compile(r'([a-z0-9][a-z0-9+.-]*)(?::[a-z0-9-]+)?\b')


def recorded_test_profiles(buildinfo):
    """Require the build's recorded environment before interpreting <!nocheck>."""
    environment = buildinfo.get('Environment', '').splitlines()
    values = {}
    for variable in ['DEB_BUILD_PROFILES', 'DEB_BUILD_OPTIONS']:
        rows = [line.strip() for line in environment if line.strip().startswith(variable + '=')]
        assert len(rows) <= 1, f'Duplicate recorded {variable}'
        if rows:
            raw = rows[0].partition('=')[2]
            assert re.fullmatch(r'"[^"\\]*"', raw), f'Invalid recorded {variable}'
            values[variable] = raw[1:-1].split()
    assert 'DEB_BUILD_PROFILES' in values, 'Conditional test SDK requires recorded build profiles'
    profiles = values['DEB_BUILD_PROFILES']
    assert all(re.fullmatch(r'[a-z0-9+./-]+', item) for item in profiles), 'Invalid recorded build profile'
    assert 'nocheck' not in profiles and 'nocheck' not in values.get('DEB_BUILD_OPTIONS', []), 'Test SDK requires checks enabled'
    return sorted(set(profiles))


def verify(record, control_text, buildinfo_text):
    control = retention.fields(control_text.split('\n\n')[0])
    buildinfo = retention.fields(buildinfo_text)
    assert control['Source'] == buildinfo['Source'] == record['source_package'], 'Wrong build source'
    assert buildinfo['Version'] == record['version'], 'Wrong build version'
    assert buildinfo['Build-Architecture'] == 'amd64', 'Wrong build architecture'
    assert hashlib.sha256(control_text.encode()).hexdigest() == record['packaging_sha256']['control'], 'Source control changed'
    wanted = {}
    for scope in ['frameworks_predecessors', 'supplementary_predecessors']:
        for node, predecessor in record.get(scope, {}).items():
            for binary in predecessor['binaries']:
                name = binary['package']
                assert name not in wanted, 'Duplicate reviewed predecessor'
                wanted[name] = {'node': node, 'version': predecessor['version'], 'architecture': binary['architecture']}
    installed = {}
    for relation in buildinfo['Installed-Build-Depends'].split(','):
        matched = RELATION.fullmatch(relation.strip())
        assert matched, f'Invalid installed build relation: {relation}'
        name, architecture, version = matched.groups()
        assert name not in installed, f'Duplicate installed package: {name}'
        installed[name] = version
        if name in wanted:
            assert version == wanted[name]['version'], f'{name}: installed {version}, reviewed {wanted[name]["version"]}'
            assert architecture is None or architecture == wanted[name]['architecture'], f'{name}: wrong installed architecture'
    required = set()
    conditional = []
    profiles = None
    for field in ['Build-Depends', 'Build-Depends-Arch', 'Build-Depends-Indep']:
        for group in control.get(field, '').split(','):
            reviewed = []
            for alternative in group.split('|'):
                name = NAME.match(alternative.strip())
                if name is None or name[1] not in wanted:
                    continue
                relation = alternative.strip()
                if relation.endswith('<!nocheck>'):
                    if profiles is None:
                        profiles = recorded_test_profiles(buildinfo)
                    relation = relation.removesuffix('<!nocheck>').strip()
                    conditional.append(name[1])
                # Other profile formulas and architecture restrictions still
                # require their own review. Never discard a condition silently.
                matched = RELATION.fullmatch(relation)
                assert matched, f'Review an unconditional exact SDK relation: {alternative}'
                package, _, version = matched.groups()
                assert version == wanted[package]['version'], f'{package}: unreviewed direct SDK version'
                reviewed.append(package)
            if reviewed:
                present = [name for name in reviewed if name in installed]
                assert present, f'Required direct predecessor absent: {reviewed}'
                required.update(present)
    assert not wanted or required, 'No reviewed direct build predecessor'
    used = sorted(set(installed) & set(wanted))
    unused = sorted(set(wanted) - set(installed))
    result = {'state': 'PASS', 'kind': 'actual-build-predecessor-version-verification',
            'source_package': record['source_package'], 'version': record['version'],
            'build_architecture': 'amd64', 'available_predecessor_count': len(wanted),
            'required_direct_predecessors': sorted(required),
            'installed_predecessors': [{'package': name, **wanted[name]} for name in used],
            'available_predecessors_not_installed': unused,
            'complete_available_input_transport': 'certified separately by the infrastructure consumer',
            'control_sha256': hashlib.sha256(control_text.encode()).hexdigest(),
            'buildinfo_sha256': hashlib.sha256(buildinfo_text.encode()).hexdigest()}
    if conditional:
        result.update(recorded_build_profiles=profiles,
                      required_test_profile_predecessors=sorted(set(conditional)),
                      test_profile_condition='<!nocheck>; recorded checks enabled')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node')
    parser.add_argument('--buildinfo', type=Path, required=True)
    parser.add_argument('--source-control', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    _, record = prepare.contract(args.node)
    control = args.source_control or ROOT/record['packaging_path']/'control'
    result = verify(record, control.read_text(), args.buildinfo.read_text())
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(f'Reviewed actual build predecessors: PASS; installed={len(result["installed_predecessors"])}; '
          f'direct={len(result["required_direct_predecessors"])}; unused available={len(result["available_predecessors_not_installed"])}')


if __name__ == '__main__':
    main()
