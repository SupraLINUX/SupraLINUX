#!/usr/bin/env python3
"""Admit individually reviewed Plasma components or supplementary providers."""
import argparse
import importlib.machinery
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
prepare = importlib.machinery.SourceFileLoader('prepare',str(ROOT/'scripts/prepare-plasma-package.py')).load_module()
fields = importlib.machinery.SourceFileLoader('retention',str(ROOT/'scripts/retain-package-artifacts.py')).load_module().fields


def check(node,record,packaging,level,material):
    assert record['packaging_review'] == 'PASS' and record['state'] == 'build-pending' and not record['attempts']
    assert record['packaging_path'] == f'packages/plasma/{node}/debian'
    if record.get('source_scope') == 'plasma-supplementary-provider':
        assert node not in level['selected_nodes'], 'Provider must not impersonate a Level 0 component'
        # Review a staging overlay using the same source authority, without
        # copying unreviewed inputs into the repository before admission.
        prepare.supplementary_contract(node, record, packaging=packaging)
    else:
        assert record.get('source_scope', 'plasma-level0') == 'plasma-level0'
        assert node in level['selected_nodes'] and node in material, 'Node is outside materialized Level 0'
        assert record['version'] == level['nodes'][node]['candidate_package_version']
        assert record['upstream_version'] == material[node]['upstream']['version']
        assert record['upstream_url'] == material[node]['upstream']['url']
        assert record['upstream_sha256'] == material[node]['upstream']['sha256']
        assert record['signature_sha256'] == material[node]['upstream']['signature_sha256']
        assert record['packaging_reference_version'] == material[node]['ubuntu_reference']['source_version']
        assert record['packaging_reference_sha256'] == material[node]['ubuntu_reference']['debian_tree_tar_sha256']
    assert prepare.packaging_hashes(packaging) == record['packaging_sha256'], 'Reviewed packaging changed'
    version = subprocess.check_output(['dpkg-parsechangelog','-l',str(packaging/'changelog'),'-S','Version'],text=True).strip()
    assert version == record['version']
    stanzas = (packaging/'control').read_text().split('\n\n')
    assert fields(stanzas[0])['Source'] == record['source_package']
    actual = {}
    for stanza in stanzas[1:]:
        control = fields(stanza)
        if 'Package' not in control:continue
        architecture = control['Architecture']
        assert architecture in {'any','linux-any','amd64','all'}, architecture
        actual[control['Package']] = 'all' if architecture == 'all' else 'amd64'
    assert actual == record['binary_packages'], 'Reviewed binary scope changed'
    assert (packaging/'tests/control').is_file() and record['review'] and all(record['review'].values())
    for name in record['required_executable_files']:
        path = packaging/name
        assert path.resolve().is_relative_to(packaging.resolve()) and path.is_file() and os.access(path,os.X_OK)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node')
    parser.add_argument('--record',type=Path,required=True)
    parser.add_argument('--packaging',type=Path,required=True)
    parser.add_argument('--admit',action='store_true',help='admit only after the current package gate is closed')
    args = parser.parse_args()
    record = json.loads(args.record.read_text())
    paths = [ROOT/'manifests/kde-plasma-package-build.json',ROOT/'manifests/kde-plasma.json',ROOT/'manifests/kde-plasma-level0.json']
    campaign,planning,level = [json.loads(path.read_text()) for path in paths]
    material = {item['node']:item for item in json.loads((ROOT/'manifests/evidence/kde-plasma-level0-materialization-result.json').read_text())['nodes']}
    check(args.node,record,args.packaging,level,material)
    if not args.admit:
        print(f'{args.node} reviewed Level 0 overlay: PASS; package execution not started')
        return
    assert campaign['authorized_nodes'] == [] and campaign['package_execution_authorized'] is False, 'Close the active package gate first'
    assert args.node not in campaign['nodes'], 'Existing package requires a repair/revalidation lifecycle'
    destination = ROOT/record['packaging_path']
    assert not destination.exists(), 'Refusing to overwrite packaging'
    shutil.copytree(args.packaging,destination,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    campaign['nodes'][args.node] = record
    campaign.update(state='execution-authorized',authorized_nodes=[args.node],package_execution_authorized=True,
                    execution_mode='preflight')
    if record.get('source_scope') == 'plasma-supplementary-provider':
        path = ROOT/'manifests/kde-plasma-supplementary-providers.json'
        providers = json.loads(path.read_text())
        provider = providers['nodes'][args.node]
        assert provider['state'] == 'packaging-preparation-pending' and not provider['package_execution_authorized']
        provider.update(state='package-build-pending',package_record=args.node,
                        package_execution_authorized=True,next_gate='authoritative-supplementary-package-input-preflight')
        provider['candidate_provider']['package_gate'] = 'execution-authorized'
        for path,data in [(paths[0],campaign),(path,providers)]:path.write_text(json.dumps(data,indent=2)+'\n')
        print(f'{args.node} supplementary provider admitted; Level 0 scope unchanged; no package Attempt')
        return
    planning['planning'].update(phase='level0-package-build',status='level0-package-build-pending',next_gate='plasma-level0-authoritative-package-build',package_execution_authorized=True,authorized_package_nodes=[args.node])
    level.update(state='package-build-authorized',next_gate=planning['planning']['next_gate'],package_execution_authorized=True,authorized_package_nodes=[args.node])
    level['scheduling'].update(package_execution_locked=False,scope='Only the individually reviewed current node; remaining Level 0 packaging stays pending')
    level['nodes'][args.node].update(state='package-build-pending',package_execution_authorized=True)
    for path,data in zip(paths,[campaign,planning,level]):path.write_text(json.dumps(data,indent=2)+'\n')
    print(f'{args.node} admitted; validate the complete lifecycle and publish one atomic Git tree before execution')


if __name__ == '__main__':main()
