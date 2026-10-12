#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
"""Plan a core desktop dependency path without authorizing an image build."""
import argparse
import hashlib
import json
from pathlib import Path


def checked_result(root, name, record):
    evidence = record.get('evidence', {})
    relative = Path(evidence.get('result_path', ''))
    assert not relative.is_absolute() and '..' not in relative.parts, 'Unsafe package evidence path'
    original = root / relative
    file = original.resolve()
    assert file.is_relative_to((root / 'manifests/evidence').resolve()) and file.is_file() and not original.is_symlink(), 'Missing package evidence'
    raw = file.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == evidence['result_sha256'], 'Package result digest'
    result = json.loads(raw)
    assert result['node'] == name and result['version'] == record['version'], 'Package result identity'
    assert result['source_commit'] == evidence['source_commit'], 'Package result commit'
    assert result['state'] == 'PASS' and result['authoritative'] is True, 'Authoritative package PASS required'
    assert all(result[field] == 'PASS' for field in ['sbuild_result', 'lintian_result', 'autopkgtest_result']), 'Incomplete package gates'
    retained = evidence.get('local_retention', {})
    assert all(retained.get(field) is True for field in ['source_complete', 'changes_complete', 'buildinfo_verified', 'offline_restore_verified']), 'Incomplete declared delivery retention'
    return {'source_package': record['source_package'], 'version': record['version'],
            'result_path': str(relative), 'result_sha256': evidence['result_sha256'],
            'source_commit': evidence['source_commit'], 'scope': 'Recorded authoritative package gates; image input byte restoration still required'}


def plan(root, profile):
    root = root.resolve()
    assert profile['schema'] == 1 and profile['state'] == 'planning-only'
    assert profile['image_build_authorized'] is False and profile['final_install_seed'] is False
    assert profile['roots'] and len(profile['roots']) == len(set(profile['roots'])), 'Invalid desktop roots'
    dag_path = root / 'manifests/kde-plasma-dag.json'
    campaign_path = root / 'manifests/kde-plasma-package-build.json'
    desktop_path = root / 'manifests/desktop-stack.json'
    dag = json.loads(dag_path.read_text())
    campaign = json.loads(campaign_path.read_text())
    desktop = json.loads(desktop_path.read_text())
    assert dag['canonical_for_package_planning'] is True, 'Canonical DAG required'
    done, active, order = set(), set(), []

    def visit(name):
        assert name in dag['nodes'], 'Unknown desktop component: ' + name
        assert name not in active, 'Desktop dependency cycle: ' + name
        if name in done:
            return
        active.add(name)
        for predecessor in sorted(dag['nodes'][name]['depends_on']):
            visit(predecessor)
        active.remove(name)
        done.add(name)
        order.append(name)

    for name in sorted(profile['roots']):
        visit(name)
    components = []
    for name in order:
        record = campaign['nodes'].get(name, {})
        row = {'node': name, 'level': dag['nodes'][name]['level'],
               'depends_on': dag['nodes'][name]['depends_on'],
               'current_state': record.get('state', 'packaging-review-pending'),
               'recorded_package_gate_pass': False, 'local_image_payload_restored': False}
        if record.get('state') == 'PASS':
            assert 'compatibility_hold' not in record, 'Unresolved package hold'
            row['recorded_package_evidence'] = checked_result(root, name, record)
            row['recorded_package_gate_pass'] = True
        components.append(row)
    passed = sum(row['recorded_package_gate_pass'] for row in components)
    return {'schema': 1, 'state': 'PLANNED; IMAGE BUILD NOT AUTHORIZED',
            'profile': profile['name'], 'profile_scope': profile['scope'],
            'profile_definition_sha256': hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'platform': desktop['platform'],
            'selected_stack': {name: desktop['desktop'][name]['version'] for name in ['plasma', 'frameworks', 'gear']},
            'inputs_sha256': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in [dag_path, campaign_path, desktop_path]},
            'roots': profile['roots'], 'components': components,
            'counts': {'core_closure': len(components), 'recorded_package_PASS': passed,
                       'package_gate_pending': len(components) - passed},
            'missing_package_gates': [row['node'] for row in components if not row['recorded_package_gate_pass']],
            'additional_image_gates': profile['additional_image_gates'],
            'final_release_gates': profile['final_release_gates'],
            'local_delivery_byte_verification': 'NOT RUN; required before composition',
            'final_install_seed': False, 'remaining_upstream_components_excluded': False,
            'image_build_authorized': False, 'image_available': False,
            'package_attempt_consumed': False, 'canonical_package_state_effect': 'none',
            'host_changes': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Refusing to overwrite an image plan'
    result = plan(args.root, json.loads(args.profile.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    counts = result['counts']
    print(f"Core image dependency plan: {counts['core_closure']} components, "
          f"{counts['recorded_package_PASS']} recorded package PASS, "
          f"{counts['package_gate_pending']} pending; image build remains unauthorized")


if __name__ == '__main__':
    main()
